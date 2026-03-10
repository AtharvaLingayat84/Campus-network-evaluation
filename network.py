import networkx as nx

G = nx.Graph()

devices = {
"Cloud": "cloud",
"Email_Server": "server",

"Main_Router": "router",
"Main_L3_Switch": "switch",

"HR_Switch": "switch",
"Finance_Switch": "switch",
"Business_Switch": "switch",
"Student_Switch": "switch",
"IT_Switch": "switch",
"Server_Switch": "switch",

"Router_Branch": "router",
"Branch_L3_Switch": "switch",
"Branch_Switch": "switch",

"HR_PC": "pc",
"HR_Printer": "printer",

"Finance_PC": "pc",
"Finance_Printer": "printer",

"Business_PC": "pc",
"Business_Printer": "printer",

"Student_PC": "pc",
"Student_Printer": "printer",

"IT_PC": "pc",
"IT_Printer": "printer",

"Web_Server": "server",
"FTP_Server": "server",

"Branch_PC1": "pc",
"Branch_PC2": "pc",
"Branch_Printer": "printer"
}

for device, dtype in devices.items():
    G.add_node(device, type=dtype)

links = [

("Email_Server","Cloud"),
("Cloud","Main_Router"),
("Main_Router","Main_L3_Switch"),

("Main_L3_Switch","HR_Switch"),
("Main_L3_Switch","Finance_Switch"),
("Main_L3_Switch","Business_Switch"),
("Main_L3_Switch","Student_Switch"),
("Main_L3_Switch","IT_Switch"),
("Main_L3_Switch","Server_Switch"),

("HR_Switch","HR_PC"),
("HR_PC","HR_Printer"),

("Finance_Switch","Finance_PC"),
("Finance_PC","Finance_Printer"),

("Business_Switch","Business_PC"),
("Business_PC","Business_Printer"),

("Student_Switch","Student_PC"),
("Student_PC","Student_Printer"),

("IT_Switch","IT_PC"),
("IT_PC","IT_Printer"),

("Server_Switch","Web_Server"),
("Server_Switch","FTP_Server"),

("Main_Router","Router_Branch"),
("Router_Branch","Branch_L3_Switch"),
("Branch_L3_Switch","Branch_Switch"),

("Branch_Switch","Branch_PC1"),
("Branch_Switch","Branch_PC2"),
("Branch_Switch","Branch_Printer")

]

G.add_edges_from(links)

nx.write_gexf(G,"campus_topology.gexf")

print("Topology exported to campus_topology.gexf")