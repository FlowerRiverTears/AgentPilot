<template>
  <div class="guide-page">
    <section class="guide-hero">
      <p class="portal-kicker">使用教程</p>
      <h1>从后台制造智能体，到前台给用户体验</h1>
      <p>
        后台负责配置模型、知识库、工具和智能体；前台只面向用户展示可用智能体，并提供对话体验。
      </p>
      <div class="guide-actions">
        <n-button type="primary" @click="router.push('/agents')">创建智能体</n-button>
        <n-button secondary @click="router.push('/portal')">进入前台</n-button>
      </div>
    </section>

    <section class="guide-grid">
      <n-card title="1. 配置模型">
        <p>进入“模型配置”，添加一个可用的大模型接口。OpenAI-compatible 接口只需要填写 Base URL、API Key 和模型名。</p>
        <p>配置完成后先点“测试”，确认接口能正常返回。</p>
      </n-card>

      <n-card title="2. 准备知识库">
        <p>知识库适合放稳定资料，例如产品手册、FAQ、制度文档、售后政策。</p>
        <p>不建议把订单、库存、用户信息这类实时数据放进知识库。</p>
      </n-card>

      <n-card title="3. 选择应用工具">
        <p>工具适合连接应用系统，例如订单查询、库存查询、工单创建、客户资料查询。</p>
        <p>创建智能体时勾选工具，用户问题命中场景时后端会自动调用。</p>
      </n-card>

      <n-card title="4. 创建智能体">
        <p>进入“智能体后台”，填写名称、描述、系统提示词，并绑定模型、知识库和工具。</p>
        <p>智能体创建后会自动出现在前台体验页，前台不会单独维护另一套智能体数据。</p>
      </n-card>

      <n-card title="5. 前台体验">
        <p>点击右上角“进入前台”，用户只会看到智能体列表和聊天窗口。</p>
        <p>前台不显示后台菜单，用户体验和后台管理保持分离。</p>
      </n-card>

      <n-card title="6. 回答来源策略">
        <p>通用问题由大模型直接回答；文档问题优先检索知识库；实时业务问题优先调用工具。</p>
        <p>如果没有可靠依据，智能体应该说明无法确认，而不是编造。</p>
      </n-card>
    </section>

    <n-card title="推荐配置示例">
      <div class="guide-example">
        <div>
          <strong>客服助手</strong>
          <p>知识库：产品手册、售后政策、常见问题</p>
          <p>工具：订单查询、物流查询、工单创建</p>
        </div>
        <div>
          <strong>内部运营助手</strong>
          <p>知识库：运营流程、报表口径、培训资料</p>
          <p>工具：库存查询、客户资料、数据看板</p>
        </div>
      </div>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";

const router = useRouter();
</script>
