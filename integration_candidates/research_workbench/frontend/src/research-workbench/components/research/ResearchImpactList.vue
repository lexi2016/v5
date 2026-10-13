<script setup lang="ts">
import { chipList, deskText, text, type LaneRow } from "../../composables/useResearchLane";

defineProps<{ rows: Array<LaneRow>; assessed?: boolean }>();
</script>

<template>
  <aside class="hourly-priority-pane" aria-label="股票层">
    <div class="hourly-panel-head">
      <div><span class="hourly-eyebrow">股票层</span><h3>priority · 股票研报</h3></div>
      <span class="hourly-pill">{{ assessed === false ? "未生成" : `${rows.length} 主线` }}</span>
    </div>
    <div class="hourly-impact-list">
      <article
        v-for="row in rows"
        :key="text(row.stock_code)"
        class="hourly-impact-card"
        :class="{ observe: !text(row.formal_overlap) && !text(row.stage_overlap) }"
      >
        <span class="hourly-source-tag key">{{ deskText(row.evidence_level || row.research_status) }}</span>
        <div class="hourly-impact-title">{{ text(row.stock_name || row.name) }} {{ text(row.stock_code || row.code) }}</div>
        <div class="hourly-impact-reason">{{ text(row.latest_evidence_sentence || row.evidence_sentence || row.research_status || row.gate_status) }}</div>
        <div class="hourly-chips">
          <span v-for="chip in chipList(row)" :key="chip" class="hourly-chip">{{ chip }}</span>
        </div>
        <div class="stock-timeline">
          <div v-for="event in (row._timeline ?? []).slice(0, 3)" :key="text(event.event_id)" class="stock-timeline-event">
            <div class="stock-timeline-head">
              <span>{{ text(event.event_time).slice(11, 16) }}</span>
              <span>{{ deskText(event.claim_type || event.evidence_level) }}</span>
            </div>
            <div class="stock-timeline-body">{{ text(event.evidence_sentence).slice(0, 150) }}</div>
          </div>
        </div>
      </article>
      <div v-if="!rows.length" class="empty">{{ assessed === false ? '股票研究主线未生成；归档原文不自动成为股票结论。' : '当前情报日无股票主线。' }}</div>
    </div>
  </aside>
</template>

