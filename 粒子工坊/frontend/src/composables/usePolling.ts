/** 轮询：enabled 为真时立即执行一次，之后每 intervalMs 执行；enabled 变假或卸载时停止 */
import { onBeforeUnmount, watch, type Ref } from "vue";

export function usePolling(fn: () => void | Promise<void>, intervalMs: number, enabled: Ref<boolean>) {
  let timer: number | undefined;
  let busy = false;

  const tick = async () => {
    // 上一次还没返回就跳过，避免慢请求堆积
    if (busy) return;
    busy = true;
    try {
      await fn();
    } finally {
      busy = false;
    }
  };

  const stop = () => {
    if (timer !== undefined) window.clearInterval(timer);
    timer = undefined;
  };

  watch(
    enabled,
    (on) => {
      stop();
      if (!on) return;
      void tick();
      timer = window.setInterval(() => void tick(), intervalMs);
    },
    { immediate: true },
  );

  onBeforeUnmount(stop);
}
