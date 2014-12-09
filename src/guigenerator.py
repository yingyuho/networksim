#!/usr/bin/env python
import sys
import networkx as nx

from Tkinter import Tk, Label, Button, Text, Scrollbar, BOTH, END, INSERT

import matplotlib
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, 
    NavigationToolbar2TkAgg)

matplotlib.use('TkAgg')

'''GUI generator displays a gui that helps you build a network and 
print it out to a user specified file'''
class GUIGenerator(object):
    def __init__(self, fileOutpath=sys.stdout):
        '''Initialize and run the gui'''
        #the fileOutpath is the file path of the file we write 
        #the results of the built network to
        self.fileOutpath=fileOutpath
        self.root= Tk()
        #list of components of the network we are building
        #(hosts, routers, links, flows)
        self.edgeList=[]
        self.hostList=[]
        self.flowList=[]
        self.routerList=[]
        #labels of nodes on the graph (displayed on the graph gui)
        self.labels={}
        #network graph object
        self.networkGraph=nx.Graph()
        #sets size and starting position of the GUI
        self.root.geometry("800x750+100+20")
        self.initUI()
          
        
    def initUI(self):
        '''Sets up the GUI that is displayed to the user'''
        self.root.title("Network Generator")     
        
        #figure containing the graph
        self.networkPlot = Figure(tight_layout=True)
        
        #plots-plots are the objects that are actually updated
        self.network = self.networkPlot.add_subplot(111)
        #enable autoscaling
        self.network.autoscale(enable=True) 
        
        #set up canvas, which holds figure containinf the graph
        canvas1 = FigureCanvasTkAgg(self.networkPlot, master=self.root)
        canvas1.show()
        canvas1.get_tk_widget().place(x=0, y=0, height=400, width=800)
        
        #draw the empty graph (graph initially displayed as a white space
        #until nodes are added)
        nx.draw(self.networkGraph,pos=nx.spring_layout(self.networkGraph),
                ax=self.network,nodelist=self.networkGraph.nodes())
        #draw the network plot on the canvas
        self.networkPlot.canvas.draw()
        
        #labels and textfields for links: 
        #buttons and textfields 1-5 are for links
        #buttons and textfields 6-9 are for entering flows
        #each number designating a label matches up with the 
        #textfield it describes
        label1 = Label(self.root, text="Device 1") 
        label1.place(x=100, y=450)   
        textfield1= Text(self.root)
        textfield1.config(width=10, height=1)
        textfield1.place(x=100, y=480)
        
        label2 = Label(self.root, text="Device 2") 
        label2.place(x=200, y=450)    
        textfield2= Text(self.root)
        textfield2.config(width=10, height=1)
        textfield2.place(x=200, y=480)       
        
        label3 = Label(self.root, text="Link Rate(Mbps)") 
        label3.place(x=300, y=450)    
        textfield3= Text(self.root)
        textfield3.config(width=10, height=1)
        textfield3.place(x=300, y=480)  
        
        label4 = Label(self.root, text="Link Delay(ms)") 
        label4.place(x=400, y=450)  
        textfield4= Text(self.root)
        textfield4.config(width=10, height=1)
        textfield4.place(x=400, y=480)  
        
        label5 = Label(self.root, text="Link Buffer(KB)") 
        label5.place(x=500, y=450)    
        textfield5= Text(self.root)
        textfield5.config(width=10, height=1)
        textfield5.place(x=500, y=480)  
        
        #labels for flows and corresponding textfields: 
        #buttons and textfields 6-9 are for flows
        label6 = Label(self.root, text="Flow Source") 
        label6.place(x=100, y=510)   
        textfield6= Text(self.root)
        textfield6.config(width=10, height=1)
        textfield6.place(x=100, y=530)  
        
        label7 = Label(self.root, text="Flow Destination") 
        label7.place(x=200, y=510)      
        textfield7= Text(self.root)
        textfield7.config(width=10, height=1)
        textfield7.place(x=200, y=530)  
        
        label8 = Label(self.root, text="Data Amount(MB)") 
        label8.place(x=300, y=510)      
        textfield8= Text(self.root)
        textfield8.config(width=10, height=1)
        textfield8.place(x=300, y=530)  
        
        label9 = Label(self.root, text="Flow Start(s)") 
        label9.place(x=400, y=510)     
        textfield9= Text(self.root)
        textfield9.config(width=10, height=1)
        textfield9.place(x=400, y=530)          
        
        #put in buttons that call update functions when pressed
        button1 = Button(self.root, text="Add Host", width=10, 
                         command= lambda: self.addHost())
        button1.place(x=0,y=420)
        button2 = Button(self.root, text="Add Router", width=10, 
                         command= lambda: self.addRouter())
        button2.place(x=100,y=420)
        # the 1.0 means row 1 column 0
        # we take the text entered in the textfields and send that to the 
        # update functions as parameters
        # you need the strip() function to get rid of the newline character
        # automatically place at the end of each text entry
        button3 = Button(self.root, text="Add Link", width=10, command= lambda: 
                         self.addEdge((textfield1.get("1.0", END).strip(),
                                       textfield2.get("1.0", END).strip(),
                                       textfield3.get("1.0", END).strip(),
                                       textfield4.get("1.0", END).strip(),
                                       textfield5.get("1.0", END).strip())))
        button3.place(x=0,y=480)
        button4 = Button(self.root, text="Add Flow", width=10, command= lambda: 
                         self.addFlow((textfield6.get("1.0", END).strip(),
                                       textfield7.get("1.0", END).strip(),
                                       textfield8.get("1.0", END).strip(),
                                       textfield9.get("1.0", END).strip())))
        button4.place(x=0,y=530)  
        
        #list of flows entered:
        #whenever a new flow is entered (and is unique) it is 
        #displayed in this pane
        self.flowlistgui = Text(self.root)
        self.flowlistgui.config(width=95, height=7)
        self.flowlistgui.place(x=0,y=590)
        
        #scrollbar for flow list
        scrollbar = Scrollbar(self.root)   
        scrollbar.config(command=self.flowlistgui.yview)
        self.flowlistgui.config(yscrollcommand=scrollbar.set)
        scrollbar.place(x=750,y=590, height=120)  
        
        #label that goes above flow list
        label10 = Label(self.root, text="Flow List") 
        label10.place(x=370, y=565)   
        
        #write to text file button: writing to the text file also
        #closes out the gui
        button5 = Button(self.root, text="Write to File", width=10, 
                        command= lambda: self.writeToFile(self.fileOutpath))
        button5.place(x=370,y=720)          
        
        
        
    def updateNetworkGraph(self):
        '''update the graph showing the network you have built thus far'''
        #clear the previous drawing of the network
        self.network.clear()
        #set the position of the nodes in the graph
        pos=nx.spring_layout(self.networkGraph)
        #routers are red
        nx.draw_networkx_nodes(self.networkGraph,pos,
                               nodelist=self.routerList,
                               node_color='r',
                               node_size=500,
                           alpha=0.8,ax=self.network)
        #hosts are blue
        nx.draw_networkx_nodes(self.networkGraph,pos,
                               nodelist=self.hostList,
                               node_color='b',
                               node_size=500,
                           alpha=0.8,ax=self.network)     
        #edges are green (flows are not shown on the graph)
        nx.draw_networkx_edges(self.networkGraph,pos,
                               edgelist=self.edgeList,
                               width=8,alpha=0.5,edge_color='g',
                               ax=self.network)  
        #finally put the labels in the graph for the nodes
        nx.draw_networkx_labels(self.networkGraph,pos,self.labels,
                                font_size=16,ax=self.network)
        #redraw the canvas
        self.networkPlot.canvas.draw()
        
    def addEdge(self, edge):
        '''Adds the specified edge to the network provided it is unique'''
        #check that the source and destination exist and that the edge 
        #isnt already present
        if((edge[0] in self.hostList or edge[0] in self.routerList) and 
           (edge[1] in self.hostList or edge[1] in self.routerList)
           and edge not in self.edgeList):
            self.edgeList.append(edge)
            #update the network graph
            self.networkGraph.add_edge(edge[0],edge[1])
            self.updateNetworkGraph()
            
    def addRouter(self):
        '''Adds a new router to our network'''
        #routers are automatically assigned names, just increment the number of 
        #routers and that is the new name of the new router
        routerNum=len(self.routerList)+1
        self.routerList.append('R%d'%(routerNum))
        #update the network graph on the gui
        self.networkGraph.add_node('R%d'%(routerNum))
        self.labels['R%d'%(routerNum)]='R%d'%(routerNum)
        self.updateNetworkGraph()
        
    def addHost(self):
        '''Adds a new host to our network'''
        #just like routers, host names are automatically assigned by 
        #incrementing the number of hosts
        hostNum=len(self.hostList)+1
        self.hostList.append('H%d'%(hostNum))
        #update the network graph on the gui
        self.networkGraph.add_node('H%d'%(hostNum))
        self.labels['H%d'%(hostNum)]='H%d'%(hostNum)
        self.updateNetworkGraph()
        
    def addFlow(self, flow):
        '''Adds the specified flow to the network provided 
        it is unique'''
        #check that the source and destination are hosts and the 
        #flow is unique
        if(flow[0] in self.hostList and flow[1] in self.hostList 
           and flow not in self.flowList):
            self.flowList.append(flow)
            #update the list of flows on the gui
            self.flowlistgui.insert(INSERT, flow)
            self.flowlistgui.insert(INSERT, '\n')
            
    def writeToFile(self, filedesc=sys.stdout):
        '''Writes out the network representation to the file specified
        as an argument'''
        if isinstance(filedesc, file):
            f = filedesc
        else:
            f = open(filedesc, mode='w')

        #write out hosts
        for host in self.hostList:
            f.write(host+'\n')
        #components are seperated by a dash
        f.write('-\n')
        #write out routers
        for router in self.routerList:
            f.write(router+'\n')
        f.write('-\n')
        #writer out edges
        for link in self.edgeList:
            f.write(" ".join(map(str, link)) + '\n')
        f.write('-\n')
        #finally write out flows
        for flow in self.flowList:
            f.write(" ".join(map(str, flow)) + '\n')

        f.close()
        #closes out the GUI after generating the network file
        self.root.destroy()
        #and end the program
        sys.exit(0)
        
if __name__ == '__main__':
    gui= GUIGenerator() 
    #call the mainloop of the root to display 
    #the gui and keep it running
    gui.root.mainloop()   