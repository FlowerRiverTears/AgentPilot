<template>
  <div class="guide-page">
    <section class="guide-hero">
      <p class="portal-kicker">{{ t('guide.title') }}</p>
      <h1>{{ t('guide.heroTitle') }}</h1>
      <p>
        {{ t('guide.heroDesc') }}
      </p>
      <div class="guide-actions">
        <n-button type="primary" @click="router.push('/agents')">{{ t('guide.createAgent') }}</n-button>
        <n-button secondary @click="router.push('/portal')">{{ t('guide.goToPortal') }}</n-button>
      </div>
    </section>

    <section class="guide-grid">
      <n-card :title="t('guide.step1Title')">
        <p>{{ t('guide.step1Desc1') }}</p>
        <p>{{ t('guide.step1Desc2') }}</p>
      </n-card>

      <n-card :title="t('guide.step2Title')">
        <p>{{ t('guide.step2Desc1') }}</p>
        <p>{{ t('guide.step2Desc2') }}</p>
      </n-card>

      <n-card :title="t('guide.step3Title')">
        <p>{{ t('guide.step3Desc1') }}</p>
        <p>{{ t('guide.step3Desc2') }}</p>
      </n-card>

      <n-card :title="t('guide.step4Title')">
        <p>{{ t('guide.step4Desc1') }}</p>
        <p>{{ t('guide.step4Desc2') }}</p>
      </n-card>

      <n-card :title="t('guide.step5Title')">
        <p>{{ t('guide.step5Desc1') }}</p>
        <p>{{ t('guide.step5Desc2') }}</p>
      </n-card>

      <n-card :title="t('guide.step6Title')">
        <p>{{ t('guide.step6Desc1') }}</p>
        <p>{{ t('guide.step6Desc2') }}</p>
      </n-card>
    </section>

    <n-card :title="t('guide.exampleTitle')">
      <div class="guide-example">
        <div>
          <strong>{{ t('guide.exampleCS') }}</strong>
          <p>{{ t('guide.exampleCSKB') }}</p>
          <p>{{ t('guide.exampleCSTools') }}</p>
        </div>
        <div>
          <strong>{{ t('guide.exampleOps') }}</strong>
          <p>{{ t('guide.exampleOpsKB') }}</p>
          <p>{{ t('guide.exampleOpsTools') }}</p>
        </div>
      </div>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";

const { t } = useI18n();
const router = useRouter();
</script>
