from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI

class Mytopo(Topo):
    def __init__(self):
        Topo.__init__(self)
        host1=self.addHost("h1")
        host2=self.addHost("h2")
        h3=self.addHost("h3")
        s1=self.addSwitch("s1", cls=OVSSwitch, protocols="OpenFlow13", datapath="user", dpctl="tuntap", ofproto="openflow13", use_p4=True)
        s2=self.addSwitch("s2", cls=OVSSwitch, protocols="OpenFlow13", datapath="user", dpctl="tuntap", ofproto="openflow13", use_p4=True)
        s3=self.addSwitch("s3", cls=OVSSwitch, protocols="OpenFlow13", datapath="user", dpctl="tuntap", ofproto="openflow13", use_p4=True)
        s4=self.addSwitch("s4", cls=OVSSwitch, protocols="OpenFlow13", datapath="user", dpctl="tuntap", ofproto="openflow13", use_p4=True)
        s5=self.addSwitch("s5", cls=OVSSwitch, protocols="OpenFlow13", datapath="user", dpctl="tuntap", ofproto="openflow13", use_p4=True)
        s6=self.addSwitch("s6", cls=OVSSwitch, protocols="OpenFlow13", datapath="user", dpctl="tuntap", ofproto="openflow13", use_p4=True)
        s7=self.addSwitch("s7", cls=OVSSwitch, protocols="OpenFlow13", datapath="user", dpctl="tuntap", ofproto="openflow13", use_p4=True)
        s8=self.addSwitch("s8", cls=OVSSwitch, protocols="OpenFlow13", datapath="user", dpctl="tuntap", ofproto="openflow13", use_p4=True)
        s9=self.addSwitch("s9", cls=OVSSwitch, protocols="OpenFlow13", datapath="user", dpctl="tuntap", ofproto="openflow13", use_p4=True)
        s10=self.addSwitch("s10", cls=OVSSwitch, protocols="OpenFlow13", datapath="user", dpctl="tuntap", ofproto="openflow13", use_p4=True)
        s11=self.addSwitch("s11", cls=OVSSwitch, protocols="OpenFlow13", datapath="user", dpctl="tuntap", ofproto="openflow13", use_p4=True)
        s12=self.addSwitch("s12", cls=OVSSwitch, protocols="OpenFlow13", datapath="user", dpctl="tuntap", ofproto="openflow13", use_p4=True)
        s13=self.addSwitch("s13", cls=OVSSwitch, protocols="OpenFlow13", datapath="user", dpctl="tuntap", ofproto="openflow13", use_p4=True)
        s14=self.addSwitch("s14", cls=OVSSwitch, protocols="OpenFlow13", datapath="user", dpctl="tuntap", ofproto="openflow13", use_p4=True)
        self.addLink(host1,s1)
        self.addLink(s1,s2)
        self.addLink(s3,s2)
        self.addLink(s3,s4)
        self.addLink(s4,s6)
        self.addLink(s5,s2)
        self.addLink(s5,s6)
        self.addLink(s5,s13)
        self.addLink(s6,s8)
        self.addLink(s6,s7)
        self.addLink(s7,s10)
        self.addLink(s8,s9)
        self.addLink(s8,s12)
        self.addLink(s9,s10)
        self.addLink(s9,s11)
        self.addLink(s11,host2)
        self.addLink(s12,s14)
        self.addLink(s12,s13)
        self.addLink(s13,s14)
        self.addLink(s14,h3)

topos={"mytopo":(lambda:Mytopo())}

def run():
    topo = MyTopo()
    net = Mininet(topo=topo, controller=RemoteController)
    net.start()

    # 启动 BMv2 交换机并连接远程控制器
    net.get('s1').start([RemoteController('c1', ip='127.0.0.1', port=6653)])

    # 启动 Mininet CLI
    CLI(net)
    net.stop()

if __name__ == '__main__':
    run()