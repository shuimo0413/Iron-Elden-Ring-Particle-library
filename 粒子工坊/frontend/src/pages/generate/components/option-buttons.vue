<script setup lang="ts">
/** 按钮组：尺寸、类别、色调、描边、对称、变体数（全部单选）；类别联动只显示「推荐」标记，不强制改值 */
import { computed } from "vue";
import type { OptionItem, OptionsPayload, RunOptions } from "@/api/option";

const props = defineProps<{ catalog: OptionsPayload }>();
const options = defineModel<RunOptions>("options", { required: true });

/** 当前类别推荐的按钮值，如 { size: 64, symmetry: "rotational" } */
const recommended = computed<Partial<Record<keyof RunOptions, string | number>>>(
  () => props.catalog.recommendations.category?.[options.value.category] ?? {},
);

function isRecommended(field: keyof RunOptions, value: string | number): boolean {
  return recommended.value[field] === value;
}

function swatchStyle(item: OptionItem) {
  if (!item.anchors.length) return {};
  const stops = item.anchors.map(([r, g, b]) => `rgb(${r},${g},${b})`).join(", ");
  return { background: `linear-gradient(90deg, ${stops})` };
}

function update<K extends keyof RunOptions>(field: K, value: RunOptions[K]) {
  options.value = { ...options.value, [field]: value };
}
</script>

<template>
  <a-card size="small" title="按钮">
    <div class="group">
      <div class="label">尺寸</div>
      <a-radio-group :value="options.size" button-style="solid" @update:value="update('size', $event)">
        <a-radio-button v-for="spec in catalog.sizes" :key="spec.size" :value="spec.size">
          {{ spec.size }}×{{ spec.size }}
          <a-tag v-if="isRecommended('size', spec.size)" color="gold" class="recommend">推荐</a-tag>
        </a-radio-button>
      </a-radio-group>
      <div class="muted hint">
        <template v-for="spec in catalog.sizes" :key="spec.size">
          <span v-if="spec.size === options.size">
            透明边 {{ spec.margin_px }}px · 最多 {{ spec.max_colors }} 色 · 覆盖率
            {{ Math.round(spec.min_coverage * 100) }}%–{{ Math.round(spec.max_coverage * 100) }}%
          </span>
        </template>
      </div>
    </div>

    <div class="group">
      <div class="label">类别</div>
      <a-radio-group :value="options.category" button-style="solid" @update:value="update('category', $event)">
        <a-radio-button v-for="item in catalog.categories" :key="item.value" :value="item.value">
          {{ item.label }}
        </a-radio-button>
      </a-radio-group>
    </div>

    <div class="group">
      <div class="label">色调</div>
      <a-radio-group :value="options.palette" button-style="solid" @update:value="update('palette', $event)">
        <a-radio-button v-for="item in catalog.palettes" :key="item.value" :value="item.value">
          <span v-if="item.anchors.length" class="palette-swatch" :style="swatchStyle(item)" />
          {{ item.label }}
        </a-radio-button>
      </a-radio-group>
    </div>

    <div class="group">
      <div class="label">描边</div>
      <a-radio-group :value="options.outline" button-style="solid" @update:value="update('outline', $event)">
        <a-radio-button v-for="item in catalog.outlines" :key="item.value" :value="item.value">
          {{ item.label }}
        </a-radio-button>
      </a-radio-group>
    </div>

    <div class="group">
      <div class="label">对称</div>
      <a-radio-group :value="options.symmetry" button-style="solid" @update:value="update('symmetry', $event)">
        <a-radio-button v-for="item in catalog.symmetries" :key="item.value" :value="item.value">
          {{ item.label }}
          <a-tag v-if="isRecommended('symmetry', item.value)" color="gold" class="recommend">推荐</a-tag>
        </a-radio-button>
      </a-radio-group>
    </div>

    <div class="group">
      <div class="label">变体数</div>
      <a-radio-group :value="options.variants" button-style="solid" @update:value="update('variants', $event)">
        <a-radio-button v-for="count in catalog.variant_counts" :key="count" :value="count">{{ count }}</a-radio-button>
      </a-radio-group>
      <div class="muted hint">变体越多越容易挑到好的，模型调用成本按变体数线性增长</div>
    </div>
  </a-card>
</template>

<style scoped>
.group + .group {
  margin-top: 16px;
}

.label {
  margin-bottom: 6px;
  font-weight: 500;
}

.hint {
  margin-top: 4px;
  font-size: 12px;
}

.recommend {
  margin: 0 0 0 4px;
  font-size: 11px;
  line-height: 16px;
  padding: 0 4px;
}

.palette-swatch {
  display: inline-block;
  width: 18px;
  height: 10px;
  margin-right: 4px;
  border-radius: 2px;
  vertical-align: middle;
}
</style>
