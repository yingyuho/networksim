#!/usr/bin/env python
from Tkinter import Tk, Label, BOTH

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
from matplotlib.figure import Figure
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('TkAgg')


class Graphics(object):
    def __init__(self):
        self.root= Tk()
        #sets size and starting position of the GUI
        self.root.geometry("1270x780+100+20")
        self.initGraphs()
        self.initUI()
        #set up the dictionaries mapping device ids to a tuple (x_series,y_series) of arrays containing data for the time series
        self.pkt_loss_dict={}
        self.buf_level_dict={}
        self.link_flow_rate_dict={}
        self.flow_rate_dict={}
        self.packet_RTT_dict={}
        self.host_send_rate_dict={}
        self.window_size_dict = {}
        #set up the labels on the graphs
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
        # label6 = Label(self.root, text="Host Send/Recieve Rate")
        label6 = Label(self.root, text="Window Size")
        label6.place(x=1125, y=655)

    def initGraphs(self):
        #figure
        self.packet_loss_graph = Figure(tight_layout=True)
        self.buffer_occupancy_graph= Figure(tight_layout=True)
        self.link_flow_rate_graph= Figure(tight_layout=True)
        self.flow_rate_graph= Figure(tight_layout=True)
        self.packet_RTT_graph= Figure(tight_layout=True)
        # self.host_send_rate_graph= Figure(tight_layout=True)
        self.window_size_graph= Figure(tight_layout=True)

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

        # self.host_send_rate_plot=self.host_send_rate_graph.add_subplot(111)
        # self.host_send_rate_plot.set_title('Host Send/Recieve Rate')
        # self.host_send_rate_plot.set_xlabel('Time (seconds)')
        # self.host_send_rate_plot.set_ylabel('Packets/Second')
        # self.host_send_rate_plot.autoscale(enable=True)

        self.window_size_plot = self.window_size_graph.add_subplot(111)
        self.window_size_plot.set_title('Window Size')
        self.window_size_plot.set_xlabel('Time (seconds)')
        self.window_size_plot.set_ylabel('Packets')
        self.window_size_plot.autoscale(enable=True)


    def initUI(self):
        self.root.title("Network Simulator Graphs")

        #set up canvases, which hold graphs
        canvas1 = FigureCanvasTkAgg(self.packet_loss_graph, master=self.root)
        canvas1.show()
        canvas1.get_tk_widget().place(x=30, y=0, height=140, width=1230)

        canvas2 = FigureCanvasTkAgg(self.buffer_occupancy_graph, master=self.root)
        canvas2.show()
        canvas2.get_tk_widget().place(x=30, y=130, height=140, width=1230)

        canvas3 = FigureCanvasTkAgg(self.link_flow_rate_graph, master=self.root)
        canvas3.show()
        canvas3.get_tk_widget().place(x=30, y=260, height=140, width=1230)

        canvas4 = FigureCanvasTkAgg(self.flow_rate_graph, master=self.root)
        canvas4.show()
        canvas4.get_tk_widget().place(x=30, y=390, height=140, width=1230)

        canvas5 = FigureCanvasTkAgg(self.packet_RTT_graph, master=self.root)
        canvas5.show()
        canvas5.get_tk_widget().place(x=30, y=520, height=140, width=1230)

        # canvas6 = FigureCanvasTkAgg(self.host_send_rate_graph, master=self.root)
        canvas6 = FigureCanvasTkAgg(self.window_size_graph, master=self.root)
        canvas6.show()
        canvas6.get_tk_widget().place(x=30, y=650, height=140, width=1230)

    def update(self, update_str):
        args=update_str.split()
        time=args[0]
        id=args[2]
        value=float(args[3])

        #need a more sophisticated update for the graphs, right now it just append to the list to graph, clears
        #the existing graph, and regraphs it, but that is unnecessarily slow


        if args[1]=="packet_loss_rate":
            if(id in self.pkt_loss_dict.keys()):
                currTime, currValue=self.pkt_loss_dict[id]
                currTime.append(float(time))
                currValue.append(value)
                self.pkt_loss_dict[id]=(currTime, currValue)
            else:
                self.pkt_loss_dict[id]=([float(time)],[value])


        elif args[1]=="buf_level":
            if(id in self.buf_level_dict.keys()):
                currTime, currValue=self.buf_level_dict[id]
                currTime.append(float(time))
                currValue.append(value)
                self.buf_level_dict[id]=(currTime, currValue)
            else:
                self.buf_level_dict[id]=([float(time)],[value])


        elif args[1]=="link_flow_rate":
            if(id in self.link_flow_rate_dict.keys()):
                currTime, currValue = self.link_flow_rate_dict[id]
                currTime.append(float(time))
                currValue.append(value)
                self.link_flow_rate_dict[id]=(currTime, currValue)
            else:
                self.link_flow_rate_dict[id]=([float(time)],[value])


        elif args[1]=="packet_rtt":
            if(id in self.packet_RTT_dict.keys()):
                currTime, currValue=self.packet_RTT_dict[id]
                currTime.append(float(time))
                currValue.append(value)
                self.packet_RTT_dict[id]=(currTime, currValue)
            else:
                self.packet_RTT_dict[id]=([float(time)],[value])


        elif args[1]=="flow_send_rate":
            if(id in self.flow_rate_dict.keys()):
                currTime, currValue=self.flow_rate_dict[id]
                currTime.append(float(time))
                currValue.append(value)
                self.flow_rate_dict[id]=(currTime, currValue)
            else:
                self.flow_rate_dict[id]=([float(time)],[value])


        # elif args[1]=="host_send_rate":
        #     if(id in self.host_send_rate_dict.keys()):
        #         currTime, currValue=self.host_send_rate_dict[id]
        #         currTime.append(float(time))
        #         currValue.append(value)
        #         self.host_send_rate_dict[id]=(currTime, currValue)
        #     else:
        #         self.host_send_rate_dict[id]=([float(time)],[value])

        elif args[1]=="window_size":
            if(id in self.window_size_dict.keys()):
                currTime, currValue=self.window_size_dict[id]
                currTime.append(float(time))
                currValue.append(value)
                self.window_size_dict[id]=(currTime, currValue)
            else:
                self.window_size_dict[id]=([float(time)],[value])

    def redraw(self):
        self.packet_loss_plot.clear()
        for id in self.pkt_loss_dict.keys():
            self.packet_loss_plot.plot(self.pkt_loss_dict[id][0],self.pkt_loss_dict[id][1],label=id)
            self.packet_loss_plot.legend(loc='lower right', numpoints = 1 )
        #Need both of these to rescale
        self.packet_loss_plot.relim()
        self.packet_loss_plot.autoscale_view()
        self.packet_loss_graph.tight_layout()
        self.packet_loss_plot.set_ylim(bottom=0)
        self.packet_loss_graph.canvas.draw()

        self.buffer_occupancy_plot.clear()
        for id in self.buf_level_dict.keys():
            self.buffer_occupancy_plot.plot(self.buf_level_dict[id][0],self.buf_level_dict[id][1],label=id)
            self.buffer_occupancy_plot.legend(loc='lower right', numpoints = 1 )
        #Need both of these to rescale
        self.buffer_occupancy_plot.relim()
        self.buffer_occupancy_plot.autoscale_view()
        self.buffer_occupancy_plot.set_ylim(bottom=0)
        self.buffer_occupancy_graph.canvas.draw()

        self.link_flow_rate_plot.clear()
        for id in self.link_flow_rate_dict.keys():
            self.link_flow_rate_plot.plot(self.link_flow_rate_dict[id][0],self.link_flow_rate_dict[id][1],label=id)
            self.link_flow_rate_plot.legend(loc='lower right', numpoints = 1 )
        #Need both of these to rescale
        self.link_flow_rate_plot.relim()
        self.link_flow_rate_plot.autoscale_view()
        self.link_flow_rate_plot.set_ylim(bottom=0)
        self.link_flow_rate_graph.canvas.draw()

        self.packet_RTT_plot.clear()
        for id in self.packet_RTT_dict.keys():
            self.packet_RTT_plot.plot(self.packet_RTT_dict[id][0],self.packet_RTT_dict[id][1],label=id)
            self.packet_RTT_plot.legend(loc='lower right', numpoints = 1 )
        #Need both of these to rescale
        self.packet_RTT_plot.relim()
        self.packet_RTT_plot.autoscale_view()
        self.packet_RTT_plot.set_ylim(bottom=0)
        self.packet_RTT_graph.canvas.draw()

        self.flow_rate_plot.clear()
        for id in self.flow_rate_dict.keys():
            self.flow_rate_plot.plot(self.flow_rate_dict[id][0],self.flow_rate_dict[id][1],label=id)
            self.flow_rate_plot.legend(loc='lower right', numpoints = 1 )
        #Need both of these to rescale
        self.flow_rate_plot.relim()
        self.flow_rate_plot.autoscale_view()
        self.flow_rate_plot.set_ylim(bottom=0)
        self.flow_rate_graph.canvas.draw()

        # self.host_send_rate_plot.clear()
        # for id in self.host_send_rate_dict.keys():
        #     self.host_send_rate_plot.plot(self.host_send_rate_dict[id][0],self.host_send_rate_dict[id][1],label=id)
        #     self.host_send_rate_plot.legend(loc='lower right', numpoints = 1 )
        #     self.host_send_rate_graph.canvas.draw()
        # #Need both of these to rescale
        # self.host_send_rate_plot.relim()
        # self.host_send_rate_plot.autoscale_view()

        self.window_size_plot.clear()
        for id in self.window_size_dict.keys():
            self.window_size_plot.plot(self.window_size_dict[id][0],self.window_size_dict[id][1],label=id)
            self.window_size_plot.legend(loc='lower right', numpoints = 1 )
        #Need both of these to rescale
        self.window_size_plot.relim()
        self.window_size_plot.autoscale_view()
        self.window_size_plot.set_ylim(bottom=0)
        self.window_size_graph.canvas.draw()

if __name__ == '__main__':
    graphs= Graphics()
    while True:
        try:
            msg = raw_input()
            if not msg:
                break
        except:
            break
        graphs.update(msg)
    graphs.redraw()
    graphs.root.mainloop()
