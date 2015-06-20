import pandas 
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import FOAF, RDF, SKOS, OWL, RDFS
from rdflib.namespace import Namespace
from collections import OrderedDict, defaultdict
from countrycode import countrycode

class TagLifter:
    """A class for convering HXL-style tagged data into RDF linked data
    guided by an OWL ontology. Builds an rdflib graph when build_graph method is called.
    
    Arguments:
    ontology - the path to the ontology to use during conversion [Required]
    source - the path to the data file to use during conversion (type determined by file extension) [Required]
    
    Values that can be set:
    
    .limit_rows - useful during debug to limit the number of rows of the data file processed by build_graph()
    
    Currently only csv files are handled
    """
    
    def clean_string(self,string):
        invalid_chars = ''.join(c for c in map(chr, range(256)) if not c.isalnum())
        return str(string).translate(None,invalid_chars)
    
    def load_data(self,source):
           """Load data from a CSV file"""
           self.source = pandas.read_csv(source)
           self.map_tags()


            
    def load_ontology(self,ontology):
        """
        Load the ontology and set the default namespace
        """
        self.onto = Graph()
        self.onto.parse(ontology, format="xml")
        for prefix, ns in self.onto.namespaces():
            if prefix == "":
                self.ontology_string = str(ns)
                self.ontology = Namespace(ns)
                return True
                
        self.ontology_string = "http://localhost/def/"
        self.ontology = Namespace(self.ontology_string)
            
    
    def map_tags(self):   
        """Searches the first 25 rows of the dataset for #tags indicating the contents of a column.
        
        Uses these as column headers where they are available."""
        data = self.source
        mapping = OrderedDict()
        for line, row in data[0:25].iterrows():
            tag_count = 0
            for key in row.keys():
                if str(row[key])[0] == "#":
                    mapping[key] = row[key]
                    tag_count +=1
                else:
                    new_key = self.clean_string(key.title())
                    mapping[key] = new_key[0].lower()+new_key[1:]
            if tag_count > 3: # We assume we've found the tag row once we've got a row with more than 3 tags in
                #Remove the tag row
                data = data.drop(line)
                break         

        if(tag_count < 3):
            print "No column tagging found in first 25 rows."
        else:
            data = data.rename(columns=mapping)

        data = data.fillna("")
        self.map = data
    
    
    def get_country(self,row):
        country = self.default_country
        if "#country+code" in row.keys():
            country = row['#country+code']
        if (len(country) < 2) and ("#country" in row.keys()):
            if row.get('#country',"xx") in self.country_cache.keys():
                country = self.country_cache[row.get('#country',"xx")]
            else:
                country = countrycode(codes=[row.get('#country',"")],origin='country_name',target="iso2c")[0]
                self.country_cache[row.get('#country',"xx")] = country

        return country.lower()
        
        
    def get_language(self,row):
        lang = row.get("#language",default=self.default_language)
        if len(lang) > 1:
            return lang
        else:
            return self.default_language

    def get_tag_type(self,tag):
        if tag in self.type_cache.keys():
            tag_type = self.type_cache[tag]
        else:
            if ( URIRef(self.ontology[tag.title()]), RDF.type, OWL.Class ) in self.onto:
                tag_type = "Class"
            elif ( URIRef(self.ontology[tag]), RDF.type, OWL.ObjectProperty ) in self.onto:
                tag_type = "ObjectProperty"
            elif ( URIRef(self.ontology[tag]), RDF.type, OWL.DatatypeProperty ) in self.onto:
                tag_type = "DataProperty"
            else: 
                tag_type = "Unknown"
            
            self.type_cache[tag] = tag_type
        return tag_type
 
    def generate_identifier(path,row,country = "xx"):
        if "#" + path + "+identifier" in row.keys(): #Check if this entity already has an identifier given in a column
            if not row["#" + path + "+identifier"].strip() == "":
                return row["#" + path + "+identifier"].strip()

        # If not, we need to work out what kind of entity we are dealing with, and then generate an identifier
        entity = path.split("+")[-1]

        if "#"+path in row.keys(): # Is there a column that might contain a name (e.g. for #participant+company+identifier do we have a #participant+company column we can use?)
            cache_key = country + entity + clean_string(row["#"+path])
            if cache_key in id_cache.keys() and len(clean_string(row["#"+path]).strip()) > 1:
                return id_cache[cache_key]

            if entity == "project":
                identifier = country + "/" + generate_project_identifier(row["#"+path])
            elif entity == "country":
                identifier = get_country(row).upper()
            else:
                identifier = country + "/" + uuid64.hex()

            id_cache[cache_key] = identifier
        else: # We had nothing to work with, so just general a UUID
            identifier = country + "/" + uuid64.hex()

        return identifier

    # Create a new entity of a given class (entity_type)
    def create_entity(g,entity_type,path,row):
        identifier = generate_identifier(entity_type,row,get_country(row))
        entity = URIRef(base_uri+ entity_type.title()+"/"+identifier )
        g.add((entity,RDF.type,URIRef(ontology+entity_type.title())))
        if path in row.keys(): # Check if this tag exists along (i.e. not with attributes) and if so, use this for the name
            g.add((entity,SKOS.prefLabel,Literal(row[path])))

        return entity 


    def build_graph(self):
        """
        Taking the mapped data in self.map and the ontology, build out a graph.
        
        As we work through the tags, we set:
        
        tag_path - an array of the components of a tag
        current_path - a string to identify the current path
        last_class - the most recent top-level class we encountered 
        last_path - the last path we were dealing with
        
        We build a cache of known entities in entity_cache identified by their path
        """
        if self.limit_rows: # During testing we may wish to only run against a limited number of rows
            data = self.map[0:self.limit_rows]
        else:
            data = self.map
            
        for line, row in data.iterrows():
            
            country = self.get_country(row)
            lang = self.get_language(row)
            last_class = ""
            last_path = ""
            
            for key in row.keys():
                col_lang = lang
                current_path = ""

                tag_path = key.split("+")
                
                for n in range(len(tag_path)):
                    tag = tag_path[n]
                    if (not tag.isdigit()) and len(tag) > 2: #If this is a digit, we skip.
                    
                        current_path += "+"+tag if not current_path == "" else tag
                        if tag[0] == "#":
                            tag = tag[1:]
                    
                        # Check if we are dealing with an entity count
                        if (tag_path[n+1] if len(tag_path) > n+1 else '').isdigit():
                            current_path += "+"+tag_path[n+1] 

                        if len((tag_path[n+1] if len(tag_path) > n+1 else '')) == 2:
                            col_lang = tag_path[n+1] 
                        
                        print current_path + " " + col_lang
                        
                        print self.ontology[tag]
                        
                        tag_type = self.get_tag_type(tag)
                        if tag_type == "Class":
                            # Check if it is in the entity cache
                            
                        
                        print tag_type
                        ## Now check if we're dealing with a class
                        
    
    
    
    def __init__(self, ontology = None, source = None, base = "http://localhost/data/"):
        self.country_cache = {}
        self.type_cache = {}
        self.default_language = "en"
        self.default_country = "xx"
        self.graph = Graph()
        if ontology:
            self.load_ontology(ontology)
        if source:
            self.load_data(source)

