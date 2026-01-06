目录结构
sdn/
│
├── onos-app/                    # 自定义 ONOS 应用（Java / OSGi）
│   ├── pom.xml
│   ├── src/main/java/org/xxx/qosapp/
│   │   ├── QosRoutingComponent.java   # 组件入口 @Component
│   │   ├── QosPacketProcessor.java    # 需求发现：拦截 PACKET_IN
│   │   ├── QosFlowInstaller.java      # 封装下发流表逻辑
│   │   ├── LinkQualityCollector.java  # （可选）调用 ONOS 统计接口，整理链路质量
│   │   └── rest/                      # ONOS 内部 REST northbound
│   │       ├── QosWebResource.java    # 提供给 Python Web 的 REST 接口
│   └── src/main/resources/
│       ├── app.xml                    # ONOS 应用描述
│       └── OSGI-INF/blueprint/
│           └── blueprint.xml
│
├── webapp/                      # Python Web 应用（路径计算 + 管理界面）
│   ├── backend/                 # 后端（Flask / FastAPI 推荐）
│   │   ├── app.py               # 启动脚本
│   │   ├── config.py            # ONOS 地址、认证、定时任务配置
│   │   ├── models/              # 数据模型（Host、Link、Demand、Path）
│   │   │   ├── graph_model.py   # 拓扑图 & 链路权重管理
│   │   │   └── demand_model.py  # 通信需求记录
│   │   ├── services/
│   │   │   ├── topo.py   # 调 ONOS REST / 自定义 REST
│   │   │   ├── qos_metric_service.py  # 链路质量计算（延迟/丢包/带宽）
│   │   │   └── route.py     # 最短路计算（Dijkstra、KSP 等）
│   │   └── db/                  # 持久化（SQLite / MySQL / Redis）
│   │       └── models.py
│   │
│   └── frontend/                # 前端页面（可选：React/Vue 或简单模板）
│       ├── static/
│       └── templates/
│           ├── index.html       # 总览：拓扑 + 链路质量 + 需求列表
│           └── topo_view.html   # 拓扑可视化（可以 embed js 图）
│
├── mininet/                     # Mininet 相关脚本
│   ├── topo/
│   │   └── qos_topo.py          # 自定义拓扑类（链路带宽、延迟等）
│   ├── probes/                  # 探测脚本（主动测链路质量）
│   │   ├── link_probe.py        # h1-h2 之间发 probe，统计 RTT/丢包
│   │   └── start_probes.sh      # 一键在各 host 上启动探测进程
│   └── run_mininet.sh           # 一键启动拓扑并连 ONOS
│
│
├── configs/
│   ├── onos.json                # ONOS IP/端口/应用名 等
│   ├── routing_policy.yaml      # 路由策略：权重配比（时延、带宽、丢包）
│   └── demands_sample.json      # 示例通信需求
│
└── tests
    ├── test_routing_service.py  # 路由算法单测
    ├── test_onos_client.py      # ONOS REST 调用测试
    └── test_e2e_flow.py         # 端到端：需求 → 最短路 → 流表下发
