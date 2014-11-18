#!/usr/bin/env python

from Tkinter import Tk, Label, BOTH

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
from matplotlib.figure import Figure
import matplotlib
matplotlib.use('TkAgg')


class Graphics(object):
    def __init__(self):
        self.root= Tk()
        #sets size and starting position of the GUI
        self.root.geometry("1270x750+100+20")
        self.initGraphs()
        self.initUI()
        #set up the dictionaries mapping device ids to a tuple (x_series,y_series) of arrays containing data for the time series
        self.pkt_loss_dict={}
        self.buf_level_dict={}
        self.link_flow_rate_dict={}
        self.flow_rate_dict={}
        self.packet_RTT_dict={}
        self.host_send_rate_dict={}
        
        self.root.mainloop()   
        
    def initGraphs(self):
        #figure
        self.packet_loss_graph = Figure(figsize=(5,4))
        self.buffer_occupancy_graph= Figure(figsize=(5,4))
        self.link_flow_rate_graph= Figure(figsize=(5,4))
        self.flow_rate_graph= Figure(figsize=(5,4))
        self.packet_RTT_graph= Figure(figsize=(5,4))
        self.host_send_rate_graph= Figure(figsize=(5,4))
        
        #plots-plots are the objects that are actually updated
        self.packet_loss_plot = self.packet_loss_graph.add_subplot(111)
        self.packet_loss_plot.set_title('Packet Loss')
        self.packet_loss_plot.set_xlabel('Time (seconds)')
        self.packet_loss_plot.set_ylabel('Packets/Second') 
        #enable autoscaling
        self.packet_loss_plot.autoscale(enable=True)
        
        self.buffer_occupancy_plot=self.buffer_occupancy_graph.add_subplot(111)
        self.buffer_occupancy_plot.set_title('Buffer Occupany')
        self.buffer_occupancy_plot.set_xlabel('Time (seconds)')
        self.buffer_occupancy_plot.set_ylabel('Kb')     
        self.buffer_occupancy_plot.autoscale(enable=True)
        
        self.link_flow_rate_plot=self.link_flow_rate_graph.add_subplot(111)
        self.link_flow_rate_plot.set_title('Link Flow Rate')
        self.link_flow_rate_plot.set_xlabel('Time (seconds)')
        self.link_flow_rate_plot.set_ylabel('Packets/Second')         
        self.link_flow_rate_plot.autoscale(enable=True)
        
        self.flow_rate_plot=self.flow_rate_graph.add_subplot(111)
        self.flow_rate_plot.set_title('Flow Send/Recieve Rate')
        self.flow_rate_plot.set_xlabel('Time (seconds)')
        self.flow_rate_plot.set_ylabel('Packets/Second')         
        self.flow_rate_plot.autoscale(enable=True)
        
        self.packet_RTT_plot=self.packet_RTT_graph.add_subplot(111)
        self.packet_RTT_plot.set_title('Average Round Trip Delay')
        self.packet_RTT_plot.set_xlabel('Time (seconds)')
        self.packet_RTT_plot.set_ylabel('Delay (seconds)')         
        self.packet_RTT_plot.autoscale(enable=True)
        
        self.host_send_rate_plot=self.host_send_rate_graph.add_subplot(111)
        self.host_send_rate_plot.set_title('Host Send/Recieve Rate')
        self.host_send_rate_plot.set_xlabel('Time (seconds)')
        self.host_send_rate_plot.set_ylabel('Packets/Second')         
        self.host_send_rate_plot.autoscale(enable=True)
        
        
    def initUI(self):
        self.root.title("Networking Graphs")
        
        #set up canvases, which hold graphs
        canvas1 = FigureCanvasTkAgg(self.packet_loss_graph, master=self.root)
        canvas1.show()
        canvas1.get_tk_widget().place(x=30, y=60, height=100, width=1230)
        
        canvas2 = FigureCanvasTkAgg(self.buffer_occupancy_graph, master=self.root)
        canvas2.show()
        canvas2.get_tk_widget().place(x=30, y=160, height=100, width=1230)        
        
        canvas3 = FigureCanvasTkAgg(self.link_flow_rate_graph, master=self.root)
        canvas3.show()
        canvas3.get_tk_widget().place(x=30, y=260, height=100, width=1230)      
        
        canvas4 = FigureCanvasTkAgg(self.flow_rate_graph, master=self.root)
        canvas4.show()
        canvas4.get_tk_widget().place(x=30, y=370, height=100, width=1230)      
        
        canvas5 = FigureCanvasTkAgg(self.packet_RTT_graph, master=self.root)
        canvas5.show()
        canvas5.get_tk_widget().place(x=30, y=490, height=100, width=1230)      
        
        canvas6 = FigureCanvasTkAgg(self.host_send_rate_graph, master=self.root)
        canvas6.show()
        canvas6.get_tk_widget().place(x=30, y=610, height=100, width=1230)       
        
           
        
        #how to change font size?
        
        label1 = Label(self.root, text="Network Simulator Graphs")
        label1.place(x=575, y=0)
        label9 = Label(self.root, text="Links")
        label9.place(x=620, y=40)  
        label3 = Label(self.root, text="Packet Loss")
        label3.place(x=30, y=50) 
        label6 = Label(self.root, text="Buffer Occupancy")
        label6.place(x=30, y=150)     
        label10 = Label(self.root, text="Flow Rate")
        label10.place(x=30, y=250)     
        label8 = Label(self.root, text="Flows")
        label8.place(x=620, y=360)         
        label4 = Label(self.root, text="Send/Recieve Rate")
        label4.place(x=30, y=370)          
        label2 = Label(self.root, text="Packet RTT")
        label2.place(x=30, y=480)        
        label7 = Label(self.root, text="Hosts")
        label7.place(x=620, y=590)               
        label5 = Label(self.root, text="Send/Recieve Rate")
        label5.place(x=30, y=600)        
              


    ##update format
    #Packet loss: [time] pkt_loss [link_id] [num_lost_since_last_update] 
    #Buffer occupancy level: [time] buf_level [link_id] [level_kb]
    #Link Flow Rate: [time] link_flow_rate [link_id] [flow_rate]
    #Packet round trip delay: [time] packet_RTT [flow_id] [average_delay_on_interval]
    #Flow Send/Recieve Rate: [time] flow_send_rate [flow_id] [rate]
    #Host Send/Recieve Rate: [time] host_send_rate [host_id] [rate]
    def update(self, update_str):
        args=update_str.split()
        time=args[0]
        id=args[2]
        value=args[3]
        
        if args[1]=="pkt_loss":
            if(id in self.pkt_loss_dict.keys()):
                self.pkt_loss_dict[id]=(self.pkt_loss_dict[id][0].append(float(time)), self.pkt_loss_dict[id][1].append(int(value)))
            else:
                self.pkt_loss_dict[id]=([float(time)],[int(value)])
        elif args[1]=="buf_level":
            if(id in self.buf_level_dict.keys()):
                self.buf_level_dict[id]=(self.buf_level_dict[id][0].append(float(time)), self.buf_level_dict[id][1].append(int(value)))
            else:
                self.buf_level_dict[id]=([float(time)],[int(value)])
        elif args[1]=="link_flow_rate":
            if(id in self.link_flow_rate_dict.keys()):
                self.link_flow_rate_dict[id]=(self.link_flow_rate_dict[id][0].append(float(time)), self.link_flow_rate_dict[id][1].append(int(value)))
            else:
                self.link_flow_rate_dict[id]=([float(time)],[int(value)])
        elif args[1]=="packet_RTT":
            if(id in self.packet_RTT_dict.keys()):
                self.packet_RTT_dict[id]=(self.packet_RTT_dict[id][0].append(float(time)), self.packet_RTT_dict[id][1].append(int(value)))
            else:
                self.packet_RTT_dict[id]=([float(time)],[int(value)])
        elif args[1]=="flow_send_rate":
            if(id in self.flow_rate_dict.keys()):
                self.flow_rate_dict[id]=(self.flow_rate_dict[id][0].append(float(time)), self.flow_rate_dict[id][1].append(int(value)))
            else:
                self.flow_rate_dict[id]=([float(time)],[int(value)])
        elif args[1]=="host_send_rate":
            if(id in self.host_send_rate_dict.keys()):
                self.host_send_rate_dict[id]=(self.host_send_rate_dict[id][0].append(float(time)), self.host_send_rate_dict[id][1].append(int(value)))
            else:
                self.host_send_rate_dict[id]=([float(time)],[int(value)])
            
        
        
if __name__ == '__main__':
    graphs= Graphics()  

