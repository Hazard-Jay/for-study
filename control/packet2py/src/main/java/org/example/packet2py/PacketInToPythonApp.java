package org.example.packet2py;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.util.Locale;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import org.onlab.packet.Ethernet;
import org.onlab.packet.MacAddress;
import org.onosproject.core.ApplicationId;
import org.onosproject.core.CoreService;
import org.onosproject.net.DeviceId;
import org.onosproject.net.PortNumber;
import org.onosproject.net.flow.DefaultTrafficSelector;
import org.onosproject.net.flow.DefaultTrafficTreatment;
import org.onosproject.net.flow.TrafficSelector;
import org.onosproject.net.flow.TrafficTreatment;
import org.onosproject.net.packet.DefaultOutboundPacket;
import org.onosproject.net.packet.InboundPacket;
import org.onosproject.net.packet.OutboundPacket;
import org.onosproject.net.packet.PacketContext;
import org.onosproject.net.packet.PacketPriority;
import org.onosproject.net.packet.PacketProcessor;
import org.onosproject.net.packet.PacketService;
import org.osgi.service.component.annotations.Activate;
import org.osgi.service.component.annotations.Component;
import org.osgi.service.component.annotations.Deactivate;
import org.osgi.service.component.annotations.Reference;
import org.osgi.service.component.annotations.ReferenceCardinality;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@Component(immediate = true)
public class PacketInToPythonApp {

    private final Logger log = LoggerFactory.getLogger(getClass());

    private static final String PY_SERVICE_URL = "http://127.0.0.1:8000/pushFlows";

    private ApplicationId appId;
    private final InternalPacketProcessor processor = new InternalPacketProcessor();

    private final ExecutorService httpPool = Executors.newFixedThreadPool(2);
    private final ConcurrentHashMap<String, Long> recent = new ConcurrentHashMap<>();
    private final long dedupMs = 3000;

    @Reference(cardinality = ReferenceCardinality.MANDATORY)
    protected CoreService coreService;

    @Reference(cardinality = ReferenceCardinality.MANDATORY)
    protected PacketService packetService;

    @Activate
    protected void activate() {
        appId = coreService.registerApplication("org.example.packet2py");
        packetService.addProcessor(processor, PacketProcessor.director(10));
        requestIntercepts();
        log.info("PacketInToPythonApp started, appId={}", appId.id());
    }

    @Deactivate
    protected void deactivate() {
        withdrawIntercepts();
        packetService.removeProcessor(processor);
        httpPool.shutdownNow();
        log.info("PacketInToPythonApp stopped");
    }

    private void requestIntercepts() {
        TrafficSelector s1 = DefaultTrafficSelector.builder().matchEthType(Ethernet.TYPE_ARP).build();
        TrafficSelector s2 = DefaultTrafficSelector.builder().matchEthType(Ethernet.TYPE_IPV4).build();
        packetService.requestPackets(s1, PacketPriority.REACTIVE, appId);
        packetService.requestPackets(s2, PacketPriority.REACTIVE, appId);
    }

    private void withdrawIntercepts() {
        TrafficSelector s1 = DefaultTrafficSelector.builder().matchEthType(Ethernet.TYPE_ARP).build();
        TrafficSelector s2 = DefaultTrafficSelector.builder().matchEthType(Ethernet.TYPE_IPV4).build();
        packetService.cancelPackets(s1, PacketPriority.REACTIVE, appId);
        packetService.cancelPackets(s2, PacketPriority.REACTIVE, appId);
    }

    private class InternalPacketProcessor implements PacketProcessor {
        @Override
        public void process(PacketContext context) {
            if (context.isHandled()) {
                return;
            }

            InboundPacket inPkt = context.inPacket();
            Ethernet eth = inPkt.parsed();
            if (eth == null) {
                return;
            }

            DeviceId deviceId = inPkt.receivedFrom().deviceId();
            PortNumber inPort = inPkt.receivedFrom().port();

            short et = eth.getEtherType();
            if (et == Ethernet.TYPE_ARP) {
                flood(context, deviceId, inPkt.unparsed());
                return;
            }

            if (et != Ethernet.TYPE_IPV4) {
                return;
            }

            MacAddress srcMac = eth.getSourceMAC();
            MacAddress dstMac = eth.getDestinationMAC();

            String key = srcMac.toString().toLowerCase(Locale.ROOT) + "->" + dstMac.toString().toLowerCase(Locale.ROOT);
            long now = System.currentTimeMillis();
            Long last = recent.get(key);
            if (last != null && now - last < dedupMs) {
                return;
            }
            recent.put(key, now);

            httpPool.submit(() -> callPythonService(srcMac, dstMac, deviceId, inPort));
        }
    }

    private void flood(PacketContext context, DeviceId deviceId, ByteBuffer data) {
        TrafficTreatment t = DefaultTrafficTreatment.builder().setOutput(PortNumber.FLOOD).build();
        OutboundPacket out = new DefaultOutboundPacket(deviceId, t, data.duplicate());
        packetService.emit(out);
        context.block();
    }

    private void callPythonService(MacAddress srcMac,
                                   MacAddress dstMac,
                                   DeviceId deviceId,
                                   PortNumber inPort) {
        HttpURLConnection conn = null;
        try {
            URL url = new URL(PY_SERVICE_URL);
            conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setConnectTimeout(1000);
            conn.setReadTimeout(3000);
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "application/json");

            String json = String.format(Locale.ROOT,
                    "{ \"srcMac\": \"%s\", \"dstMac\": \"%s\", \"deviceId\": \"%s\", \"inPort\": \"%s\" }",
                    srcMac.toString(), dstMac.toString(), deviceId.toString(), inPort.toString());

            try (OutputStream os = conn.getOutputStream()) {
                os.write(json.getBytes(StandardCharsets.UTF_8));
            }

            int code = conn.getResponseCode();
            if (code / 100 == 2) {
                log.info("pushFlows OK, HTTP {}", code);
            } else {
                log.warn("pushFlows FAIL, HTTP {}, body={}", code, json);
            }
        } catch (Exception e) {
            log.warn("Error calling pushFlows {}", PY_SERVICE_URL, e);
        } finally {
            if (conn != null) {
                conn.disconnect();
            }
        }
    }
}
