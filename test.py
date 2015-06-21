from taglifter import TagLifter


tl = TagLifter(ontology = "test/resource-projects-ontology.rdf",source = "test/eiti-project-level.csv",base="http://www.resourceprojects.org/",
            source_meta={"author":"Tim Davies","Source_Type":"official","Converted":"Today"})

tl.limit_rows = 2
tl.build_graph()

print(tl.graph.serialize(format='turtle',destination="test/eiti.ttl"))
#print(tl.graph.serialize(format='n3'))



tl = TagLifter(ontology = "test/resource-projects-ontology.rdf",source = "test/openoil-concessions-indonesia.csv",base="http://www.resourceprojects.org/",
            source_meta={"author":"Tim Davies","Source_Type":"official","Converted":"Today"})

tl.limit_rows = 5
tl.build_graph()



print(tl.graph.serialize(format='turtle',destination="test/openoil.ttl"))


