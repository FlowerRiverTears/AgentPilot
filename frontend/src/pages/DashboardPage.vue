<template>
  <div class="page-grid">
    <n-page-header title="总览" subtitle="AgentPilot 第一版控制台" />
    <div class="metrics">
      <n-card title="大模型">
        <div class="metric-value">网关</div>
        <div class="muted">兼容接口 / 本地模型</div>
      </n-card>
      <n-card title="检索增强">
        <div class="metric-value">流程</div>
        <div class="muted">解析、切块、检索、引用</div>
      </n-card>
      <n-card title="切面">
        <div class="metric-value">追踪</div>
        <div class="muted">日志、审计、耗时、埋点</div>
      </n-card>
      <n-card title="向量">
        <div class="metric-value">pgvector</div>
        <div class="muted">向量化与相似度检索</div>
      </n-card>
    </div>
    <n-card title="第一版目标">
      <n-steps :current="2">
        <n-step title="项目骨架" description="FastAPI + Vue" />
        <n-step title="智能体运行" description="创建智能体并执行任务" />
        <n-step title="知识库检索增强" description="上传文档并检索引用" />
        <n-step title="开源发布" description="容器编排 + 说明文档" />
      </n-steps>
    </n-card>
  </div>
</template>
