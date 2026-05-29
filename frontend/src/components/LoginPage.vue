<script setup>
import { ref, reactive, onMounted, onUnmounted } from "vue";
import { authLogin, authRegister, setToken } from "../api";

const emit = defineEmits(["authenticated"]);

const busy = ref(false);
const error = ref("");
const mode = ref("login");
const form = reactive({ username: "", password: "" });

/* ── Eye tracking ── */
const pupils = ref([
  { x: 0, y: 0 }, // blue slime — 2 eyes
  { x: 0, y: 0 },
  { x: 0, y: 0 }, // yellow slime — 2 eyes
  { x: 0, y: 0 },
  { x: 0, y: 0 }, // white slime — 2 eyes
  { x: 0, y: 0 },
]);

const eyeRefs = ref([]);
const maxPupilOffset = 4;

function onMouseMove(e) {
  eyeRefs.value.forEach((el, i) => {
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const eyeCx = rect.left + rect.width / 2;
    const eyeCy = rect.top + rect.height / 2;
    const dx = e.clientX - eyeCx;
    const dy = e.clientY - eyeCy;
    const dist = Math.sqrt(dx * dx + dy * dy);
    const clamp = Math.min(dist, 60);
    const ratio = dist > 0 ? (clamp / 60) * maxPupilOffset : 0;
    pupils.value[i].x = dist > 0 ? (dx / dist) * ratio : 0;
    pupils.value[i].y = dist > 0 ? (dy / dist) * ratio : 0;
  });
}

function setEyeRef(i) {
  return (el) => {
    eyeRefs.value[i] = el;
  };
}

onMounted(() => window.addEventListener("mousemove", onMouseMove));
onUnmounted(() => window.removeEventListener("mousemove", onMouseMove));

/* ── Auth ── */
async function onSubmit() {
  busy.value = true;
  error.value = "";
  try {
    const { username, password } = form;
    const out = mode.value === "register" ? await authRegister(username, password) : await authLogin(username, password);
    setToken(out.token);
    emit("authenticated", out.user);
  } catch (e) {
    error.value = e?.message || String(e || "请求失败");
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="login-shell">
    <div class="login-cards">
      <!-- Left: Branding -->
      <div class="login-brand">
        <h1 class="login-title">交互式数据分析系统</h1>

        <div class="slimes">
          <!-- Blue slime (left, second tallest) -->
          <div class="slime slime--blue">
            <div class="slime__shadow"></div>
            <div class="slime__body">
              <div class="slime__eyes">
                <div class="slime__eye" :ref="setEyeRef(0)">
                  <div class="slime__pupil" :style="{ transform: `translate(${pupils[0].x}px, ${pupils[0].y}px)` }"></div>
                </div>
                <div class="slime__eye" :ref="setEyeRef(1)">
                  <div class="slime__pupil" :style="{ transform: `translate(${pupils[1].x}px, ${pupils[1].y}px)` }"></div>
                </div>
              </div>
            </div>
          </div>

          <!-- Yellow slime (center, tallest) -->
          <div class="slime slime--yellow">
            <div class="slime__shadow"></div>
            <div class="slime__body">
              <div class="slime__eyes">
                <div class="slime__eye" :ref="setEyeRef(2)">
                  <div class="slime__pupil" :style="{ transform: `translate(${pupils[2].x}px, ${pupils[2].y}px)` }"></div>
                </div>
                <div class="slime__eye" :ref="setEyeRef(3)">
                  <div class="slime__pupil" :style="{ transform: `translate(${pupils[3].x}px, ${pupils[3].y}px)` }"></div>
                </div>
              </div>
            </div>
          </div>

          <!-- White slime (right, shortest) -->
          <div class="slime slime--white">
            <div class="slime__shadow"></div>
            <div class="slime__body">
              <div class="slime__eyes">
                <div class="slime__eye" :ref="setEyeRef(4)">
                  <div class="slime__pupil" :style="{ transform: `translate(${pupils[4].x}px, ${pupils[4].y}px)` }"></div>
                </div>
                <div class="slime__eye" :ref="setEyeRef(5)">
                  <div class="slime__pupil" :style="{ transform: `translate(${pupils[5].x}px, ${pupils[5].y}px)` }"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Right: Auth form -->
      <div class="login-form-card">
        <div class="login-form__tabs">
          <button class="login-tab" :class="{ 'login-tab--active': mode === 'login' }" @click="mode = 'login'">登录</button>
          <button class="login-tab" :class="{ 'login-tab--active': mode === 'register' }" @click="mode = 'register'">注册</button>
        </div>

        <p class="error" v-if="error">{{ error }}</p>

        <form @submit.prevent="onSubmit">
          <div class="login-field">
            <input
              type="text"
              v-model="form.username"
              placeholder="用户名"
              autocomplete="username"
              required
            />
          </div>
          <div class="login-field">
            <input
              type="password"
              v-model="form.password"
              placeholder="密码不少于6位"
              autocomplete="current-password"
              required
              minlength="6"
            />
          </div>
          <button class="login-submit" type="submit" :disabled="busy">
            {{ mode === "login" ? "登 录" : "注册并登录" }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ═══════════════════════════════════════════
   Shell — full viewport gradient
   ═══════════════════════════════════════════ */

.login-shell {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #e8f4fd 0%, #ffffff 40%, #dceefb 100%);
  padding: 40px 24px;
  box-sizing: border-box;
}

/* ═══════════════════════════════════════════
   Cards container
   ═══════════════════════════════════════════ */

.login-cards {
  display: flex;
  background: #ffffff;
  border-radius: 18px;
  box-shadow: 0 2px 20px rgba(0, 0, 0, 0.06);
  overflow: hidden;
  max-width: 880px;
  width: 100%;
  min-height: 480px;
}

/* ═══════════════════════════════════════════
   Left: Brand card
   ═══════════════════════════════════════════ */

.login-brand {
  flex: 1;
  background: linear-gradient(180deg, #e3f0fa 0%, #f5f9fd 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 32px;
  border-right: 1px solid #e8edf2;
}

.login-title {
  font-family: "SF Pro Display", system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
  font-size: 28px;
  font-weight: 700;
  color: #1d1d1f;
  margin: 0 0 48px;
  letter-spacing: 0.5px;
  text-align: center;
}

.login-sub {
  font-size: 14px;
  color: #7a7a7a;
  margin: 0 0 40px;
  letter-spacing: -0.224px;
}

/* ═══════════════════════════════════════════
   Slime characters
   ═══════════════════════════════════════════ */

.slimes {
  display: flex;
  align-items: flex-end;
  gap: 20px;
  margin-top: 8px;
}

.slime {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.slime__shadow {
  width: 80%;
  height: 12px;
  background: radial-gradient(ellipse, rgba(0, 0, 0, 0.1) 0%, transparent 70%);
  border-radius: 50%;
  margin-bottom: -4px;
}

.slime__body {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* ── Blue slime (left, second tallest) ── */

.slime--blue .slime__body {
  width: 72px;
  height: 78px;
  background: linear-gradient(180deg, #7ec8f8 0%, #3b9ae1 40%, #2389d4 100%);
  border-radius: 50% 50% 50% 50% / 58% 58% 42% 42%;
  box-shadow: inset 0 -10px 18px rgba(0, 0, 0, 0.12), inset 0 6px 10px rgba(255, 255, 255, 0.35);
}

/* ── Yellow slime (center, tallest) ── */

.slime--yellow .slime__body {
  width: 88px;
  height: 100px;
  background: linear-gradient(180deg, #ffe889 0%, #f5c842 35%, #e0a800 100%);
  border-radius: 50% 50% 50% 50% / 56% 56% 44% 44%;
  box-shadow: inset 0 -12px 22px rgba(0, 0, 0, 0.12), inset 0 8px 12px rgba(255, 255, 255, 0.4);
}

/* ── White slime (right, shortest) ── */

.slime--white .slime__body {
  width: 58px;
  height: 52px;
  background: linear-gradient(180deg, #ffffff 0%, #e8ecf1 45%, #d4d9df 100%);
  border-radius: 50% 50% 50% 50% / 60% 60% 40% 40%;
  box-shadow: inset 0 -8px 14px rgba(0, 0, 0, 0.08), inset 0 4px 8px rgba(255, 255, 255, 0.7);
}

/* ── Eyes ── */

.slime__eyes {
  display: flex;
  gap: 14px;
  margin-top: -4px;
}

.slime--blue .slime__eyes { gap: 13px; margin-top: -6px; }
.slime--yellow .slime__eyes { gap: 16px; margin-top: -8px; }
.slime--white .slime__eyes { gap: 10px; margin-top: -3px; }

.slime__eye {
  width: 16px;
  height: 18px;
  background: #ffffff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.06);
}

.slime--blue .slime__eye { width: 15px; height: 17px; }
.slime--yellow .slime__eye { width: 18px; height: 21px; }
.slime--white .slime__eye { width: 12px; height: 14px; }

.slime__pupil {
  width: 7px;
  height: 8px;
  background: #1a1a1d;
  border-radius: 50%;
  transition: none;
}

.slime--blue .slime__pupil { width: 6px; height: 7px; }
.slime--yellow .slime__pupil { width: 8px; height: 9px; }
.slime--white .slime__pupil { width: 5px; height: 6px; }

/* ═══════════════════════════════════════════
   Right: Login form card
   ═══════════════════════════════════════════ */

.login-form-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 48px 40px;
}

.login-form__tabs {
  display: flex;
  gap: 24px;
  margin-bottom: 28px;
}

.login-tab {
  border: none;
  background: transparent;
  font-family: "SF Pro Display", system-ui, -apple-system, sans-serif;
  font-size: 24px;
  font-weight: 600;
  color: #c0c0c0;
  cursor: pointer;
  padding: 0 0 6px;
  border-bottom: 2px solid transparent;
  transition: color 0.2s, border-color 0.2s;
}

.login-tab--active {
  color: #1d1d1f;
  border-bottom-color: #0066cc;
}

.login-field {
  margin-bottom: 16px;
}

.login-field input {
  width: 100%;
  padding: 14px 18px;
  border: 1px solid #d9dde3;
  border-radius: 12px;
  font-family: "SF Pro Text", system-ui, -apple-system, sans-serif;
  font-size: 16px;
  color: #1d1d1f;
  background: #f9fafb;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
  box-sizing: border-box;
}

.login-field input::placeholder {
  color: #b0b5bd;
}

.login-field input:focus {
  border-color: #0066cc;
  box-shadow: 0 0 0 3px rgba(0, 102, 204, 0.1);
  background: #ffffff;
}

.login-submit {
  width: 100%;
  padding: 14px;
  margin-top: 8px;
  border: none;
  border-radius: 12px;
  background: #0066cc;
  color: #ffffff;
  font-family: "SF Pro Text", system-ui, -apple-system, sans-serif;
  font-size: 17px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s, transform 0.1s;
}

.login-submit:hover {
  background: #0071e3;
}

.login-submit:active {
  transform: scale(0.97);
}

.login-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.error {
  color: #cc331f;
  font-size: 13px;
  background: #fef6f5;
  border: 1px solid #fcd5cf;
  border-radius: 8px;
  padding: 10px 14px;
  margin-bottom: 14px;
}

/* ═══════════════════════════════════════════
   Responsive
   ═══════════════════════════════════════════ */

@media (max-width: 720px) {
  .login-cards {
    flex-direction: column;
    max-width: 400px;
  }

  .login-brand {
    border-right: none;
    border-bottom: 1px solid #e8edf2;
    padding: 36px 24px;
  }

  .login-title {
    font-size: 22px;
  }

  .slimes {
    gap: 14px;
  }

  .slime--blue .slime__body { width: 54px; height: 58px; }
  .slime--yellow .slime__body { width: 66px; height: 76px; }
  .slime--white .slime__body { width: 44px; height: 40px; }

  .login-form-card {
    padding: 32px 28px;
  }
}
</style>
