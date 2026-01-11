package org.example.packet2py;

import org.onlab.packet.Ethernet;
import org.onlab.packet.MacAddress;
import org.onosproject.core.ApplicationId;
import org.onosproject.core.CoreService;
import org.onosproject.net.DeviceId;
import org.onosproject.net.PortNumber;
import org.onosproject.net.packet.InboundPacket;
import org.onosproject.net.packet.PacketContext;
import org.onosproject.net.packet.PacketPriority;
import org.onosproject.net.packet.PacketProcessor;
import org.onosproject.net.packet.PacketService;
import org.onosproject.net.flow.TrafficSelector;
import org.onosproject.net.flow.DefaultTrafficSelector;
import org.osgi.service.component.annotations.Activate;
import org.osgi.service.component.annotations.Component;
import org.osgi.service.component.annotations.Deactivate;
import org.osgi.service.component.annotations.Reference;
import org.osgi.service.component.annotations.ReferenceCardinality;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.Locale;

@Component(immediate = true)
public class PacketInToPythonApp {

    private final Logger log = LoggerFactory.getLogger(getClass());

    private static final String DEFAULT_PY_URL = "http://172.17.0.1:8000/pushFlows";
    private static final String PY_SERVICE_URL = System.getenv().getOrDefault("PY_SERVICE_URL", DEFAULT_PY_URL);

    private ApplicationId appId;
    private final InternalPacketProcessor processor = new InternalPacketProcessor();

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
        log.info("PacketInToPythonApp stopped");
    }

    private void requestIntercepts() {
        // 只拦截 IPv4 包
        TrafficSelector.Builder s2 = DefaultTrafficSelector.builder();
        s2.matchEthType(Ethernet.TYPE_IPV4);
        packetService.requestPackets(s2.build(), PacketPriority.REACTIVE, appId);
    }

    private void withdrawIntercepts() {
        // 取消拦截 IPv4 包
        TrafficSelector.Builder s2 = DefaultTrafficSelector.builder();
        s2.matchEthType(Ethernet.TYPE_IPV4);
        packetService.cancelPackets(s2.build(), PacketPriority.REACTIVE, appId);
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

            // 只处理 IPv4 包
            if (eth.getEtherType() != Ethernet.TYPE_IPV4) {
                return;
            }

            MacAddress srcMac = eth.getSourceMAC();
            MacAddress dstMac = eth.getDestinationMAC();

            // 调用 Python 服务获取输出端口
            String outPort = callPythonService(srcMac, dstMac, deviceId, inPort);
            if (outPort != null && !outPort.isEmpty()) {
                try {
                    context.treatmentBuilder().setOutput(PortNumber.portNumber(outPort));
                    context.send();
                } catch (Exception e) {
                    log.warn("PacketOut failed, device={}, outPort={}", deviceId, outPort, e);
                }
            }
        }
    }

    private String callPythonService(MacAddress srcMac,
                                     MacAddress dstMac,
                                     DeviceId deviceId,
                                     PortNumber inPort) {
        HttpURLConnection conn = null;
        try {
            URL url = new URL(PY_SERVICE_URL);
            conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setConnectTimeout(1000);
            conn.setReadTimeout(2000);
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "application/json");

            String json = String.format(Locale.ROOT,
                    "{ \"srcMac\": \"%s\", \"dstMac\": \"%s\", \"deviceId\": \"%s\", \"inPort\": \"%s\" }",
                    srcMac.toString(),
                    dstMac.toString(),
                    deviceId.toString(),
                    inPort.toString());

            try (OutputStream os = conn.getOutputStream()) {
                os.write(json.getBytes(StandardCharsets.UTF_8));
            }

            int code = conn.getResponseCode();
            String body = readAll(code >= 200 && code < 300 ? conn.getInputStream() : conn.getErrorStream());

            if (code / 100 == 2) {
                log.info("pushFlows OK, HTTP {}", code);
                return extractOutPort(body);
            } else {
                log.warn("pushFlows FAIL, HTTP {}, url={}, body={}", code, PY_SERVICE_URL, json);
                return null;
            }
        } catch (Exception e) {
            log.warn("Error calling pushFlows {}", PY_SERVICE_URL, e);
            return null;
        } finally {
            if (conn != null) {
                conn.disconnect();
            }
        }
    }

    private static String readAll(InputStream is) throws Exception {
        if (is == null) return "";
        byte[] buf = is.readAllBytes();
        return new String(buf, StandardCharsets.UTF_8);
    }

    private static String extractOutPort(String body) {
        if (body == null) return null;
        int k = body.indexOf("\"outPort\"");
        if (k < 0) return null;
        int c = body.indexOf(":", k);
        if (c < 0) return null;
        int q1 = body.indexOf("\"", c);
        if (q1 < 0) return null;
        int q2 = body.indexOf("\"", q1 + 1);
        if (q2 < 0) return null;
        return body.substring(q1 + 1, q2);
    }
}
