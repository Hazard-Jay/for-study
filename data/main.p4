header timestamp_t {
    bit<64> timestamp;  // 时间戳字段
}

header custom_eth_t {
    bit<48> dst_addr;  // 目标 MAC 地址
    bit<48> src_addr;  // 源 MAC 地址
    bit<16> type;      // 自定义类型字段，代替 LLDP
}

struct headers_t {
    custom_eth_t ethernet;  // 自定义以太网头部
    timestamp_t timestamp;  // 时间戳字段
}

struct metadata_t {
    bit<64> delay;  // 存储计算的时延
}

// 解析报文
parser MyParser(packet_in packet,
                out headers_t hdr,
                inout metadata_t meta,
                inout standard_metadata_t standard_metadata) {

    state start {
        transition parse_ethernet;
    }

    state parse_ethernet {
        hdr.ethernet = packet.extract<custom_eth_t>();
        transition select(hdr.ethernet.type) {
            0x1234: parse_timestamp;  // 自定义类型
            default: accept;
        }
    }

    state parse_timestamp {
        hdr.timestamp = packet.extract<timestamp_t>();
        transition accept;
    }
}

// 控制逻辑：检测自定义类型包、计算时延并上报
control MyControl(inout headers_t hdr, inout metadata_t meta, inout standard_metadata_t standard_metadata) {

    bit<64> current_time = standard_metadata.timestamp;

    if (hdr.ethernet.type == 0x1234) {  // 自定义类型
        // 如果有时间戳，计算时延
        if (hdr.timestamp.timestamp != 0) {
            meta.delay = current_time - hdr.timestamp.timestamp;
            // 发送 Packet-In 上报时延数据
            packet_in(standard_metadata.ingress_port, hdr, meta);
        } else {
            // 如果没有时间戳，使用当前时间并转发包
            hdr.timestamp.timestamp = current_time;
            // 转发到所有端口
            standard_metadata.egress_spec = 0xFFFF;
        }
    }
}

// Packet-In 动作：将信息通过 Packet-In 发送到控制器
action packet_in(bit<9> ingress_port, headers_t hdr, metadata_t meta) {
    send_to_controller(ingress_port, hdr, meta.delay);
}
