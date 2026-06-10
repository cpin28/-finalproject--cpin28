"use strict";

// Web client for mealplan. Same-origin, so it talks to the REST API with plain fetch().
// Like the other clients, it owns presentation only — every bit of data comes from the API.

const $ = (sel) => document.querySelector(sel);
const status = (msg, isError = false) => {
  const el = $("#status");
  el.textContent = msg || "";
  el.style.color = isError ? "#b00020" : "var(--accent)";
};

async function api(path, options = {}) {
  const resp = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!resp.ok) {
    let detail = resp.statusText;
    try { detail = (await resp.json()).detail || detail; } catch (_) {}
    throw new Error(`${resp.status}: ${detail}`);
  }
  return resp.status === 204 ? null : resp.json();
}

// --- Tabs ---------------------------------------------------------------
document.querySelectorAll("#tabs button").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll("#tabs button").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    btn.classList.add("active");
    $(`#${btn.dataset.tab}`).classList.add("active");
    status("");
    LOADERS[btn.dataset.tab]?.();
  });
});

// --- Recipes ------------------------------------------------------------
async function loadRecipes() {
  const q = $("#recipe-search").value.trim();
  try {
    const recipes = await api("/recipes" + (q ? `?q=${encodeURIComponent(q)}` : ""));
    const list = $("#recipe-list");
    list.innerHTML = "";
    recipes.forEach((r) => {
      const li = document.createElement("li");
      li.textContent = `${r.name} · ${r.servings} servings`;
      li.addEventListener("click", () => {
        document.querySelectorAll("#recipe-list li").forEach((x) => x.classList.remove("selected"));
        li.classList.add("selected");
        showRecipe(r);
      });
      list.appendChild(li);
    });
    if (!recipes.length) list.innerHTML = '<li class="muted">No recipes.</li>';
  } catch (e) { status(e.message, true); }
}

async function showRecipe(r) {
  const d = $("#recipe-detail");
  const ingredients = r.ingredients.map((i) => `<li>${i.quantity} ${i.unit} ${i.name}</li>`).join("");
  d.innerHTML = `
    <h2>${r.name}</h2>
    <p class="muted">${r.servings} servings · ${r.prep_time_minutes} min</p>
    <span id="cook-badge" class="badge">checking…</span>
    ${r.description ? `<p>${r.description}</p>` : ""}
    <h3>Ingredients</h3><ul>${ingredients || "<li class='muted'>none</li>"}</ul>
    ${r.instructions ? `<h3>Instructions</h3><p>${r.instructions}</p>` : ""}`;
  try {
    const check = await api(`/recipes/${r.id}/can-make`);
    const badge = $("#cook-badge");
    if (check.can_make) {
      badge.className = "badge ok"; badge.textContent = "✓ Pantry has everything";
    } else {
      badge.className = "badge warn"; badge.textContent = `Missing: ${check.missing.join(", ")}`;
    }
  } catch (e) { status(e.message, true); }
}

$("#recipe-search").addEventListener("input", loadRecipes);

// --- Pantry -------------------------------------------------------------
async function loadPantry() {
  try {
    const [pantry, ingredients] = await Promise.all([api("/pantry"), api("/ingredients")]);

    const select = $("#pantry-ingredient");
    select.innerHTML = ingredients
      .map((i) => `<option value="${i.id}" data-unit="${i.default_unit}">${i.name}</option>`)
      .join("");
    syncPantryUnit();

    const tbody = $("#pantry-table tbody");
    tbody.innerHTML = "";
    pantry.forEach((p) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${p.name}</td><td>${p.quantity}</td><td>${p.unit}</td>`;
      const tdBtn = document.createElement("td");
      const rm = document.createElement("button");
      rm.className = "ghost"; rm.textContent = "remove";
      rm.addEventListener("click", async () => {
        try { await api(`/pantry/${p.ingredient_id}`, { method: "DELETE" }); loadPantry(); }
        catch (e) { status(e.message, true); }
      });
      tdBtn.appendChild(rm); tr.appendChild(tdBtn);
      tbody.appendChild(tr);
    });
    if (!pantry.length) tbody.innerHTML = '<tr><td colspan="4" class="muted">Pantry is empty.</td></tr>';
  } catch (e) { status(e.message, true); }
}

function syncPantryUnit() {
  const opt = $("#pantry-ingredient").selectedOptions[0];
  if (opt && !$("#pantry-unit").value) $("#pantry-unit").value = opt.dataset.unit || "";
}
$("#pantry-ingredient").addEventListener("change", () => { $("#pantry-unit").value = ""; syncPantryUnit(); });

$("#pantry-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = {
    ingredient_id: Number($("#pantry-ingredient").value),
    quantity: Number($("#pantry-qty").value),
    unit: $("#pantry-unit").value.trim(),
  };
  try {
    await api("/pantry", { method: "PUT", body: JSON.stringify(body) });
    $("#pantry-qty").value = "";
    status("Pantry updated.");
    loadPantry();
  } catch (e) { status(e.message, true); }
});

// --- Weekly plan --------------------------------------------------------
async function loadPlan() {
  try {
    const [plan, recipes] = await Promise.all([api("/plan"), api("/recipes")]);
    $("#plan-recipe").innerHTML = recipes.map((r) => `<option value="${r.id}">${r.name}</option>`).join("");

    const byDate = {};
    plan.forEach((m) => { (byDate[m.date] ||= []).push(m); });

    const grid = $("#plan-grid");
    grid.innerHTML = "";
    const dates = Object.keys(byDate).sort();
    if (!dates.length) { grid.innerHTML = '<p class="muted">No meals planned yet.</p>'; return; }
    dates.forEach((date) => {
      const day = document.createElement("div");
      day.className = "day";
      day.innerHTML = `<h3>${date}</h3>`;
      byDate[date].forEach((m) => {
        const slot = document.createElement("div");
        slot.className = "slot";
        slot.innerHTML = `<span><span class="meal">${m.meal_type}</span> · ${m.recipe_name}</span>`;
        const rm = document.createElement("button");
        rm.className = "ghost"; rm.textContent = "✕";
        rm.addEventListener("click", async () => {
          try { await api(`/plan/${m.id}`, { method: "DELETE" }); loadPlan(); }
          catch (e) { status(e.message, true); }
        });
        slot.appendChild(rm);
        day.appendChild(slot);
      });
      grid.appendChild(day);
    });
  } catch (e) { status(e.message, true); }
}

$("#plan-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = {
    date: $("#plan-date").value,
    meal_type: $("#plan-meal").value,
    recipe_id: Number($("#plan-recipe").value),
  };
  try {
    await api("/plan", { method: "POST", body: JSON.stringify(body) });
    status("Added to plan.");
    loadPlan();
  } catch (e) { status(e.message, true); }
});

// --- Shopping list ------------------------------------------------------
$("#shopping-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const params = new URLSearchParams();
  if ($("#shop-start").value) params.set("start", $("#shop-start").value);
  if ($("#shop-end").value) params.set("end", $("#shop-end").value);
  try {
    const items = await api("/shopping-list" + (params.toString() ? `?${params}` : ""));
    const list = $("#shopping-list");
    list.innerHTML = "";
    if (!items.length) { list.innerHTML = '<li class="muted">Nothing to buy — pantry covers the plan. 🎉</li>'; return; }
    items.forEach((it) => {
      const li = document.createElement("li");
      li.innerHTML = `<input type="checkbox"> <span>${it.quantity} ${it.unit} ${it.name}</span>`;
      list.appendChild(li);
    });
  } catch (e) { status(e.message, true); }
});

const LOADERS = { recipes: loadRecipes, pantry: loadPantry, plan: loadPlan, shopping: () => {} };

// Initial load
loadRecipes();
