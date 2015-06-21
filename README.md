# tag-lifter

Converts data from HXL-style #tagged spreadsheets to Linked Data, guided by an ontology

## Why?

Linked Data structures can be very expressive, allowing complex relationships to be captured. But most people deal with flat data, working in spreadsheets.

This tool aims to make it easy to convert flat data to richly structured linked data models, with minimal burden on the data owner. By simply adding a series of intuitive tags, it should be possible to represent entities, their relationships and properties. 

It was developed as part of the extract-transform-load layer of the prototype [ResourceProjects.org](http://github.com/NRGI/resource-projects-etl)

## Usage

Usage example:

```python
tl = TagLifter(ontology = "test/resource-projects-ontology.rdf",source = "test/openoil-concessions-indonesia.csv",base="http://www.resourceprojects.org/",
            source_meta={"creator":"Extractive Industry Transparency Initiative",})

tl.limit_rows = 5 # Just run against the first few rows for now
tl.build_graph()

tl.graph.serialize(format='turtle',destination="test/graph.ttl")

```

## Markup and ontologies

The parser reads through a CSV file, and looks for a row containing #tags which indicate how the column should be interpreted. This builds on the approach of [HXL - a simple standard for messy data](http://hxlstandard.org/).

This means you can take an existing spreadsheet, leave the column heading intact, but just add a row underneath them to mark-up details of what they contain. 

E.g: the spreadsheet:

| Date | Project Name | Project Identifier | Company with stake | Percentage Stake |
|------|------|------|------|------|
| 2014-01-01 | Jubilee Fields | gh/jufi-34fas3 | Tullow Ghana Limited | 10% |

becomes

| Date | Project Name | Project Identifier | Company with stake | Percentage Stake |
|------|------|------|------|------|
| #date | #project | #project+identifier | #project+company | #project+company+share |
| 2014-01-01 | Jubilee Fields | gh/jufi-34fas3 | Tullow Ghana Limited | 10% |

Tags can be singular (e.g. #project), or may be composite of multiple components (e.g. #project+identifier or #project+company), in which case they are interpreted as either specifying attributes, or specifying a relationship between two entities (based on information from the ontology)

The interpretation of these tags to generate an RDF graph is guided by an [OWL ontology](http://www.w3.org/TR/owl2-primer/), plus some simple rules. 

> Note, at present only some elements of OWL are supported. In particular, reasoning out of subClass / subProperty relationships is limited.
>
> The tool also currently assumes certain restrictions on an ontology. A complete list of restrictions, and tests to ensure ontologies are suitable for us 

### Processing
The script reads through each row of the spreadsheet, and left-to-right across the columns, looking at the tag for each column as it goes. 

The components of a tag should represent either:

#### A class
Tags are Title cased, and suffixed to the base URI of the ontology when looking for a related class, e.g. #project = http://example.org/ref/Project

If a tag represents a class, then:

* An entity is added to the data model for this Class
* If there is a column with a +identifier attribute, this is used as part of the identifier for this entity
* If not, custom code currently generates an identifier for this entity
* The value of the column is used as the label

The code is currently based on using a country as part of the URI for the entry. 

Language codes can be used to tag the language of a label. 

If two classes are included next to each other as neighbouring components of a tag (e.g. #project+company) then:

* If these two entities can be related directly together via some property, an entry is added to the graph relating the two;
* If a connection between these two entities can be found via some intermediary entity, then this intermediate entity, and the related properties are added to the graph.

> For example, in the ResourceProjects.org ontology, ```Project``` and ```Company``` do not have a direct relationship. Instead, they are related via a ```Stake``` entity (```Project -> hasStake -> Stake -> hasStakeholder -> Company```). The script will check for any following attributes (e.g. ```#project+company+share```) whether it should be attached to the preceding entity amongst the tag components, or the intermediate entity that has been inferred. 

#### A property
Properties are case sensitive. For example #startDate = http://example.org/ref/startDate

If a tag component is not identified as either a class or property in the ontology, a new property is written out (unless the ```allow_extra_properties``` flag of the tag-lifter object is set to ```False```)

Properties are attached to the last identified class (or intermediate entry).

When no classes have yet been found (e.g. if a property tag is found in the first column of the data) then the property is attached to an entity for the database row, as part of the provenance information recorded.

> Some typing of properties currently takes place


## ToDo

Add better handling of provenance information