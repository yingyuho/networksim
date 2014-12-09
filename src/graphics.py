from Tkinter import Tk, Label, BOTH

from matplotlib.backends.backend_tkagg import 
FigureCanvasTkAgg, NavigationToolbar2TkAgg
from matplotlib.figure import Figure
import matplotlib
matplotlib.use('TkAgg')

'''Graphics object is responsible for making the gui 
that graphs the information about the network'''
class Graphics(object):
    def __init__(self):
        '''
        Initialize the gui and set up the graphs in it
        '''
        self.root= Tk()
        #sets size and starting position of the GUI
        self.root.geometry("1270x780+100+20")
        #call functions that set up the user interface
        self.initGraphs()
        self.initUI()
        #set up the dictionaries mapping device ids to a tuple 
        #(x_series,y_series) of arrays containing data for the time series
        #whenever an update occurs, the new values are 
        #appended to the lists mapped to by the device id specified
        self.pkt_loss_dict={}
        self.buf_level_dict={}
        self.link_flow_rate_dict={}
        self.flow_rate_dict={}
        self.packet_RTT_dict={}
        self.host_send_rate_dict={}
        #set up the labels on the graphs (variable names 
        #dont matter here since they are static)
        label1 = Label(self.root, text="Packet Loss") 
        label1.place(x=1184, y=0)  
        label2 = Label(self.root, text="Buffer Occupancy") 
        label2.place(x=1151, y=135)      
        label3 = Label(self.root, text="Flow Rate") 
        label3.place(x=1196, y=265)        
        label4 = Label(self.root, text="Flow Send/Recieve Rate") 
        label4.place(x=1125, y=395)           
        label5 = Label(self.root, text="Packet RTT") 
        label5.place(x=1190, y=525)              
        label6 = Label(self.root, text="Host Send/Recieve Rate") 
        label6.place(x=1125, y=655)                    
        
    def initGraphs(self):
        '''
        Set up the graphs that are in the gui
        '''
        #figures for each of the 6 graphs: 
        #graphs are contained within figure objects
        self.packet_loss_graph = Figure(tight_layout=True)
        self.buffer_occupancy_graph= Figure(tight_layout=True)
        self.link_flow_rate_graph= Figure(tight_layout=True)
        self.flow_rate_graph= Figure(tight_layout=True)
        self.packet_RTT_graph= Figure(tight_layout=True)
        self.host_send_rate_graph= Figure(tight_layout=True)
        
        #plots-plots are the objects that are actually updated, put inside figures
        
        #packet loss plot
        self.packet_loss_plot = self.packet_loss_graph.add_subplot(111)
        self.packet_loss_plot.set_title('Packet Loss')
        self.packet_loss_plot.set_xlabel('Time (seconds)')
        self.packet_loss_plot.set_ylabel('Packets/Second') 
        #enable autoscaling
        self.packet_loss_plot.autoscale(enable=True)
        
        #buffer occupancy
        self.buffer_occupancy_plot=self.buffer_occupancy_graph.add_subplot(111)
        self.buffer_occupancy_plot.set_title('Buffer Occupany')
        self.buffer_occupancy_plot.set_xlabel('Time (seconds)')
        self.buffer_occupancy_plot.set_ylabel('Kb')     
        self.buffer_occupancy_plot.autoscale(enable=True)
        
        #flow rate across links
        self.link_flow_rate_plot=self.link_flow_rate_graph.add_subplot(111)
        self.link_flow_rate_plot.set_title('Link Flow Rate')
        self.link_flow_rate_plot.set_xlabel('Time (seconds)')
        self.link_flow_rate_plot.set_ylabel('Packets/Second')         
        self.link_flow_rate_plot.autoscale(enable=True)
        
        #flow rates (across flows)
        self.flow_rate_plot=self.flow_rate_graph.add_subplot(111)
        self.flow_rate_plot.set_title('Flow Send/Recieve Rate')
        self.flow_rate_plot.set_xlabel('Time (seconds)')
        self.flow_rate_plot.set_ylabel('Packets/Second')         
        self.flow_rate_plot.autoscale(enable=True)
        
        #packet round trip time
        self.packet_RTT_plot=self.packet_RTT_graph.add_subplot(111)
        self.packet_RTT_plot.set_title('Average Round Trip Delay')
        self.packet_RTT_plot.set_xlabel('Time (seconds)')
        self.packet_RTT_plot.set_ylabel('Delay (seconds)')         
        self.packet_RTT_plot.autoscale(enable=True)
        
        #host send and recieve rates
        self.host_send_rate_plot=self.host_send_rate_graph.add_subplot(111)
        self.host_send_rate_plot.set_title('Host Send/Recieve Rate')
        self.host_send_rate_plot.set_xlabel('Time (seconds)')
        self.host_send_rate_plot.set_ylabel('Packets/Second')         
        self.host_send_rate_plot.autoscale(enable=True)
        

        
    def initUI(self):
        '''Sets up the canvases that contain each 
        of the graphs on the main gui'''
        #set the title of the window pane
        self.root.title("Network Simulator Graphs")     
        
        #set up canvases, which hold graphs
        #packet loss
        canvas1 = FigureCanvasTkAgg(self.packet_loss_graph, master=self.root)
        canvas1.show()
        canvas1.get_tk_widget().place(x=30, y=0, height=140, width=1230)
        #buffer occupancy
        canvas2 = FigureCanvasTkAgg(self.buffer_occupancy_graph, master=self.root)
        canvas2.show()
        canvas2.get_tk_widget().place(x=30, y=130, height=140, width=1230)        
        #link flow rate
        canvas3 = FigureCanvasTkAgg(self.link_flow_rate_graph, master=self.root)
        canvas3.show()
        canvas3.get_tk_widget().place(x=30, y=260, height=140, width=1230)      
        #flow rate
        canvas4 = FigureCanvasTkAgg(self.flow_rate_graph, master=self.root)
        canvas4.show()
        canvas4.get_tk_widget().place(x=30, y=390, height=140, width=1230)      
        #packet round trip time
        canvas5 = FigureCanvasTkAgg(self.packet_RTT_graph, master=self.root)
        canvas5.show()
        canvas5.get_tk_widget().place(x=30, y=520, height=140, width=1230)      
        #host send and recieve rate
        canvas6 = FigureCanvasTkAgg(self.host_send_rate_graph, master=self.root)
        canvas6.show()
        canvas6.get_tk_widget().place(x=30, y=650, height=140, width=1230)       
        
              


    
    def update(self, update_str):
        '''
        Updates the graphs in the gui based on the 
        input update_string, which contains the information
        that is updated to the graphs
        
        update format:
        
        Packet loss: [time] pkt_loss [link_id] [num_lost_since_last_update] 
        Buffer occupancy level: [time] buf_level [link_id] [level_kb]
        Link Flow Rate: [time] link_flow_rate [link_id] [flow_rate]
        Packet round trip delay: [time] packet_RTT [flow_id] [average_delay_on_interval]
        Flow Send/Recieve Rate: [time] flow_send_rate [flow_id] [rate]
        Host Send/Recieve Rate: [time] host_send_rate [host_id] [rate]
        '''
        #split up the input string into useful values
        args=update_str.split()
        time=args[0]
        id=args[2]
        value=float(args[3])
        
        #packet loss update
        if args[1]=="pkt_loss":
            #update the packet loss dictionary by appending the time 
            #and value of the newest datapoint to the stored lists 
            if(id in self.pkt_loss_dict.keys()):
                currTime, currValue=self.pkt_loss_dict[id]
                currTime.append(float(time))
                currValue.append(value)
                self.pkt_loss_dict[id]=(currTime, currValue)
            else:
                self.pkt_loss_dict[id]=([float(time)],[value])
                
            #empty the packet loss graph since it is outdated
            self.packet_loss_plot.clear()
            
            #re-plot the packet loss graph on the gui
            for id in self.pkt_loss_dict.keys():
                self.packet_loss_plot.plot(self.pkt_loss_dict[id][0],
                                           self.pkt_loss_dict[id][1],label=id)
                #put the legend on the graph
                self.packet_loss_plot.legend(loc='lower right', numpoints = 1 )
                self.packet_loss_graph.canvas.draw()
            #rescale the packet loss plot
            self.packet_loss_plot.relim()
            self.packet_loss_plot.autoscale_view()
                     
        #buffer level update
        elif args[1]=="buf_level":
            #update the buffer level dictionary by appending the time and
            #value of the newest datapoint to the stored lists 
            if(id in self.buf_level_dict.keys()):
                currTime, currValue=self.buf_level_dict[id]
                currTime.append(float(time))
                currValue.append(value)
                self.buf_level_dict[id]=(currTime, currValue)                
            else:
                self.buf_level_dict[id]=([float(time)],[value])
                
            #empty the outdated graph
            self.buffer_occupancy_plot.clear()
            #re-plot graph
            for id in self.buf_level_dict.keys():
                self.buffer_occupancy_plot.plot(self.buf_level_dict[id][0],
                                                self.buf_level_dict[id][1],label=id)   
                self.buffer_occupancy_plot.legend(loc='lower right', numpoints = 1 )
                self.buffer_occupancy_graph.canvas.draw()
            #rescale the graph
            self.buffer_occupancy_plot.relim()
            self.buffer_occupancy_plot.autoscale_view()
                
        #link flow rate update
        elif args[1]=="link_flow_rate":
            #update the link flow rate dictionary by appending the time
            #and value of the newest datapoint to the stored lists 
            if(id in self.link_flow_rate_dict.keys()):
                currTime, currValue=link_flow_rate_dict[id]
                currTime.append(float(time))
                currValue.append(value)
                self.link_flow_rate_dict[id]=(currTime, currValue)                
            else:
                self.link_flow_rate_dict[id]=([float(time)],[value])
                
            #empty the outdated graph
            self.link_flow_rate_plot.clear()
            #re-plot graph
            for id in self.link_flow_rate_dict.keys():
                self.link_flow_rate_plot.plot(self.link_flow_rate_dict[id][0],
                                              self.link_flow_rate_dict[id][1],label=id)    
                self.link_flow_rate_plot.legend(loc='lower right', numpoints = 1 )
                self.link_flow_rate_graph.canvas.draw()
            #rescale
            self.link_flow_rate_plot.relim()
            self.link_flow_rate_plot.autoscale_view()
            
        #packet round trip time update
        elif args[1]=="packet_RTT":
            #update the packet RTT dictionary by appending the time and 
            #value of the newest datapoint to the stored lists 
            if(id in self.packet_RTT_dict.keys()):
                currTime, currValue=self.packet_RTT_dict[id]
                currTime.append(float(time))
                currValue.append(value)
                self.packet_RTT_dict[id]=(currTime, currValue)                
            else:
                self.packet_RTT_dict[id]=([float(time)],[value])
            #empty the outdated graph
            self.packet_RTT_plot.clear()
            #re-plot
            for id in self.packet_RTT_dict.keys():
                self.packet_RTT_plot.plot(self.packet_RTT_dict[id][0],
                                          self.packet_RTT_dict[id][1],label=id)  
                self.packet_RTT_plot.legend(loc='lower right', numpoints = 1 )
                self.packet_RTT_graph.canvas.draw()
            #rescale
            self.packet_RTT_plot.relim()
            self.packet_RTT_plot.autoscale_view()
            
        #flow send rate update    
        elif args[1]=="flow_send_rate":
            #update the flow rate dictionary by appending the time
            #and value of the newest datapoint to the stored lists 
            if(id in self.flow_rate_dict.keys()):
                currTime, currValue=self.flow_rate_dict[id]
                currTime.append(float(time))
                currValue.append(value)
                self.flow_rate_dict[id]=(currTime, currValue)                
            else:
                self.flow_rate_dict[id]=([float(time)],[value])
            #empty the outdated graph
            self.flow_rate_plot.clear()
            #re-plot
            for id in self.flow_rate_dict.keys():
                self.flow_rate_plot.plot(self.flow_rate_dict[id][0],
                                         self.flow_rate_dict[id][1],label=id)    
                self.flow_rate_plot.legend(loc='lower right', numpoints = 1 )
                self.flow_rate_graph.canvas.draw()
            #rescale
            self.flow_rate_plot.relim()
            self.flow_rate_plot.autoscale_view()            
        
        #host send rate update
        elif args[1]=="host_send_rate":
            #update the host send rate dictionary by appending the time 
            #and value of the newest datapoint to the stored lists 
            if(id in self.host_send_rate_dict.keys()):
                currTime, currValue=self.host_send_rate_dict[id]
                currTime.append(float(time))
                currValue.append(value)
                self.host_send_rate_dict[id]=(currTime, currValue)                
            else:
                self.host_send_rate_dict[id]=([float(time)],[value])
            #empty the outdated graph
            self.host_send_rate_plot.clear()
            #re-plot
            for id in self.host_send_rate_dict.keys():
                self.host_send_rate_plot.plot(self.host_send_rate_dict[id][0],
                                              self.host_send_rate_dict[id][1],label=id)   
                self.host_send_rate_plot.legend(loc='lower right', numpoints = 1 )
                self.host_send_rate_graph.canvas.draw()
            #rescale
            self.host_send_rate_plot.relim()
            self.host_send_rate_plot.autoscale_view()
            
if __name__ == '__main__':
    graphs= Graphics() 
    # the input is piped through to this program, 
    #so we run a while/true loop here that cuts 
    # out whenever the piped inputs stop coming 
    #(i.e. the simulation ends)
    while True:
        msg = raw_input()
        if not msg:
            break
        graphs.update(msg)
    graphs.root.mainloop()  
    