<script setup lang="ts">
import { computed, nextTick, onMounted, onBeforeUnmount, ref, watch } from "vue";

import { loadResearchLane, loadResearchLaneLatest, type ResearchLane } from "../api/research_lane";
import { latestReadQueue } from "../composables/latestReadQueue";
import { useResearchState } from "../composables/useResearchLane";
import ResearchStatusStrip from "../components/research/ResearchStatusStrip.vue";
import ResearchImpactList from "../components/research/ResearchImpactList.vue";
import ResearchFeedPane from "../components/research/ResearchFeedPane.vue";
import ResearchSourceColumns from "../components/research/ResearchSourceColumns.vue";
import ResearchContextPane from "../components/research/ResearchContextPane.vue";
import ResearchAppendix from "../components/research/ResearchAppendix.vue";
import "../styles/v3-research-lane.css";

const props = defineProps<{ archiveDate: string; initialFeedFilter?: "latest" | "wechat" }>();

const payload = ref<ResearchLane | null>(null);
const loading = ref(false);
const error = ref("");

const feedFilter = ref<string>(props.initialFeedFilter === "wechat" ? "wechat" : "latest");
const requestedMode = ref<"EXACT" | "LATEST">("EXACT");
const updateDiagnostic = computed(() => payload.value?.update_diagnostic as { state?: string; message?: string } | undefined);

const {
  stockMainline,
  stockTimeline,
  feedCards,
  feedEmptyMessage,
  sourceColumns,
  timelineRows,
  cannotItems,
  quality,
} = useResearchState(payload, feedFilter);

const wechatArticleCount = computed(() => {
  const morning = payload.value?.morning_news as Record<string, unknown> | undefined;
  return (morning?.articles as Array<unknown> | undefined)?.length ?? 0;
});

function validateResearchDate(result: ResearchLane, expectedDate?: string) {
  const actualDate = result?.research_date;
  if (result.status === "NOT_MATERIALIZED" && (actualDate === null || actualDate === "")) {
    if (expectedDate && result.requested_date !== expectedDate) {
      throw new Error(`研报决策台请求日期证据错误：响应 requested_date=${String(result.requested_date ?? "CANNOT_CONFIRM")}，请求=${expectedDate}，未展示该响应。`);
    }
    return;
  }
  if (typeof actualDate !== "string" || !actualDate) {
    throw new Error("研报决策台日期证据错误：响应缺少真实来源日期，未展示该响应。");
  }
  if (expectedDate && actualDate !== expectedDate) {
    throw new Error(`研报决策台日期证据错误：响应来源日期=${actualDate}，请求=${expectedDate}，未展示该响应。`);
  }
}

const reads = latestReadQueue<ResearchLane>({
  start() { loading.value = true; error.value = ""; payload.value = null; },
  success(result) { payload.value = result; loading.value = false; },
  failure(reason) {
    const busy = (reason as { status?: number } | null)?.status === 503;
    error.value = busy
      ? "研报只读服务仍繁忙（HTTP 503）；已完成 3 次有限尝试，请稍后按所选日期重读。未用其他日期替代。"
      : reason instanceof Error ? reason.message : "研报决策台读取失败；未用其他日期替代。";
    loading.value = false;
  },
});
onBeforeUnmount(() => reads.dispose());
function run(loader: () => Promise<ResearchLane>, expectedDate?: string) {
  reads.submit(expectedDate ? `EXACT:${expectedDate}` : "LATEST", async () => {
    const result = await loader();
    validateResearchDate(result, expectedDate);
    return result;
  });
}

function loadExact() {
  if (!props.archiveDate) return;
  requestedMode.value = "EXACT";
  const date = props.archiveDate;
  run(() => loadResearchLane(date), date);
}

function loadLatest() {
  requestedMode.value = "LATEST";
  run(loadResearchLaneLatest);
}

function locateWechatPane() {
  void nextTick(() => {
    document.querySelector(".hourly-feed-pane")?.scrollIntoView?.({ behavior: "smooth", block: "start" });
  });
}
function scrollToWechat() {
  feedFilter.value = "wechat";
  locateWechatPane();
}

watch(() => props.archiveDate, loadExact, { immediate: true });
watch(() => props.initialFeedFilter, (value) => {
  feedFilter.value = value === "wechat" ? "wechat" : "latest";
  if (value === "wechat") locateWechatPane();
});
watch(payload, (value) => {
  if (value && props.initialFeedFilter === "wechat") locateWechatPane();
});
onMounted(() => {
  if (props.initialFeedFilter === "wechat" && payload.value) locateWechatPane();
});
</script>

<template>
  <section class="research-view" role="region" aria-label="研报决策台">
    <div class="panel-head">
      <div>
        <h2>研报决策台</h2>
        <p id="researchSubtitle">研报、早盘新闻、公众号统一在此读取；只用于研究解释，不打开 BUY gate。</p>
      </div>
      <div class="panel-head-actions">
        <button type="button" class="secondary" :disabled="loading || !archiveDate" @click="loadExact">按所选日期</button>
        <button type="button" class="secondary" :disabled="loading" @click="loadLatest">查看 latest</button>
        <button type="button" class="secondary" @click="scrollToWechat">定位公众号</button>
        <span class="badge readonly">只读研究</span>
      </div>
    </div>

    <p data-testid="research-date-identity" class="research-message" role="status">
      所选日期：{{ archiveDate }} · 请求模式：{{ requestedMode }} · 实际来源日期：{{ payload?.research_date || "CANNOT_CONFIRM" }}
      <strong v-if="payload?.research_date && payload.research_date !== archiveDate"> · 来源日期与所选日期不同；仅展示显式 latest 读取的来源日。</strong>
    </p>
    <p v-if="!loading && !error && payload?.status === 'LIVE_PERIPHERAL_ONLY'" class="research-message" role="status">
      小时研报未生成，外围资料可查看
    </p>
    <p v-if="payload?.status === 'LIVE_PERIPHERAL_ONLY'" role="status" class="research-message">小时研究未生成，已有独立保存资料可阅读；不据此补算股票影响、复盘或经理决定。</p>
    <details v-if="payload?.archive_materials" class="research-message"><summary>归档来源身份与覆盖范围</summary><pre style="white-space:pre-wrap;overflow-wrap:anywhere">{{ JSON.stringify({ ...payload.archive_materials as object, articles: undefined }, null, 2) }}</pre></details>
    <p v-if="updateDiagnostic" class="research-message" role="status"><strong>{{ updateDiagnostic.state }}</strong> · <span>{{ updateDiagnostic.message }}</span></p>
    <p v-if="loading" class="research-message" role="status">正在读取研报决策台。</p>
    <p v-else-if="error" class="research-message research-error" role="alert">{{ error }}</p>
    <div v-else-if="payload?.status === 'NOT_MATERIALIZED'" class="research-message research-missing" role="status">
      <strong>NOT_MATERIALIZED</strong>
      <span>{{ payload.reason }}</span>
    </div>

    <section
      v-if="!loading && !error && payload?.status === 'NOT_MATERIALIZED'"
      class="hourly-desk hourly-desk-archive-only"
      id="hourlyInvestmentDesk"
      aria-label="公众号归档阅读区"
    >
      <div class="hourly-desk-grid">
        <ResearchImpactList :rows="[]" :assessed="false" />
        <ResearchFeedPane
          :feed-cards="[]"
          :feed-filter="feedFilter"
          :archive-date="archiveDate"
          :on-filter="(f: string) => (feedFilter = f)"
          :columns="[]"
        />
        <ResearchContextPane :timeline-rows="[]" :quality="{}" :timeline-assessed="false" />
      </div>
    </section>

    <template v-else-if="payload">
      <section class="hourly-desk" id="hourlyInvestmentDesk" aria-label="研报决策台三栏">
        <ResearchStatusStrip
          :payload="payload"
          :stock-mainline-length="stockMainline.length"
          :stock-timeline-length="stockTimeline.length"
          :wechat-article-count="wechatArticleCount"
          :on-wechat="scrollToWechat"
        />

        <section class="hourly-desk-grid">
          <ResearchImpactList :rows="stockMainline" :assessed="Array.isArray(payload.stock_research_daily)" />

          <ResearchFeedPane
            :feed-cards="feedCards"
            :feed-filter="feedFilter"
            :archive-date="archiveDate"
            :empty-message="feedEmptyMessage"
            :on-filter="(f: string) => (feedFilter = f)"
            :columns="sourceColumns"
          />

          <ResearchContextPane :timeline-rows="timelineRows" :quality="quality" :timeline-assessed="Array.isArray(payload.stock_research_timeline)" />
        </section>

        <ResearchAppendix :items="cannotItems" />
      </section>
    </template>
  </section>
</template>

