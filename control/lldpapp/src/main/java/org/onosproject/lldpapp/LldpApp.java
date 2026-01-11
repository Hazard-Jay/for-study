package org.onosproject.lldpapp;

import org.apache.http.client.methods.HttpPost;
import org.apache.http.impl.client.HttpClients;
import org.apache.http.client.methods.HttpUriRequestBase;
import org.apache.http.entity.StringEntity;
import org.apache.http.impl.client.HttpClient;
import org.apache.http.HttpResponse;
import org.onosproject.core.ApplicationId;
import org.onosproject.net.Device;
import org.onosproject.net.DeviceId;
import org.onosproject.net.PortNumber;
import org.onosproject.net.packet.PacketService;
import org.onosproject.net.packet.PacketContext;
import org.onosproject.net.packet.PacketPriority;
import org.onosproject.net.packet.PacketHandler;
import org.onosproject.net.packet.PacketIn;
import org.onosproject.net.packet.PacketOut;
import org.onosproject.net.packet.PacketOutBuilder;
import org.onosproject.net.flow.FlowRuleService;
import org.onosproject.net.flow.criteria.Criteria;
import org.onosproject.net.flow.instructions.Instruction;
import org.onosproject.net.flow.instructions.OutputInstruction;
import org.onosproject.net.flow.types.FlowEntry;
import org.onosproject.net.flow.types.FlowRuleOperations;
import org.onosproject.core.CoreService;
import org.onosproject.store.service.StorageService;
import org.onosproject.net.DeviceService;
import org.onosproject.app.Application;

import java.util.concurrent.TimeUnit;
import java.util.List;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;

public class LldpApp implements Application {
    private static final String CUSTOM_TYPE = "0x1234";  // 自定义类型
    private static final String API_URL = "http://172.17.0.1:8000/delays";  // 上传设备信息和时延的 API URL
    private static final int PERIOD = 5;  // 定时任务周期：5秒

    private CoreService coreService;
    private FlowRuleService flowRuleService;
    private PacketService packetService;
    private DeviceService deviceService;
    private ApplicationId appId;

    private final ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(1);

    @Override
    public void activate() {
        appId = coreService.registerApplication("org.onosproject.lldpapp");

        // 定时任务每 5 秒执行一次
        scheduler.scheduleAtFixedRate(this::sendPacketOutToAllSwitches, 0, PERIOD, TimeUnit.SECONDS);

        // 监听 Packet-In 消息
        packetService.addPacketListener(this::handlePacketIn, PacketPriority.REACTIVE);
    }

    @Override
    public void deactivate() {
        // 取消定时任务
        scheduler.shutdown();
    }

    // 定时向所有交换机发送自定义类型包
    private void sendPacketOutToAllSwitches() {
        List<Device> devices = deviceService.getDevices();
        for (Device device : devices) {
            sendCustomPacketOut(device.id());
        }
    }

    // 向交换机发送自定义类型包
    private void sendCustomPacketOut(DeviceId deviceId) {
        // 创建自定义类型包
        PacketOut packetOut = new PacketOutBuilder()
                .setDeviceId(deviceId)
                .setEthernetType(Integer.parseInt(CUSTOM_TYPE, 16))  // 设置自定义类型
                .setOutputPort(PortNumber.FLOOD)  // 设置端口为 Flood（广播）
                .build();

        // 通过 PacketService 发送 Packet-Out 包
        packetService.emit(packetOut);
        System.out.println("Sent Custom Packet-Out to device " + deviceId);
    }

    // 处理收到的 Packet-In 包
    private void handlePacketIn(PacketContext context) {
        // 获取收到的包的信息
        if (context.inPacket().parsed().ethType() == Integer.parseInt(CUSTOM_TYPE, 16)) {
            DeviceId deviceId = context.inPacket().receivedFrom().deviceId();
            PortNumber port = context.inPacket().receivedFrom().port();

            // 上传设备信息和端口到 HTTP API
            uploadDelayData(deviceId, port);
        }
    }

    // 上传设备信息和端口到 HTTP API
    private void uploadDelayData(DeviceId deviceId, PortNumber port) {
        try {
            HttpClient client = HttpClients.createDefault();
            HttpPost postRequest = new HttpPost(API_URL);

            // 创建 JSON 数据
            String json = String.format("{\"deviceId\": \"%s\", \"port\": \"%s\"}", deviceId.toString(), port.toString());
            StringEntity entity = new StringEntity(json);
            postRequest.setEntity(entity);
            postRequest.setHeader("Content-Type", "application/json");

            // 发送请求
            HttpResponse response = client.execute(postRequest);
            System.out.println("Uploaded delay data to " + API_URL + " with response code " + response.getStatusLine().getStatusCode());
        } catch (Exception e) {
            System.err.println("Error uploading delay data: " + e.getMessage());
        }
    }
}
