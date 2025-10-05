let CURRENT_FORM_ID = null;
let CURRENT_SCHEMA = null;

const $ = (id) => document.getElementById(id);
const apiBase = () => ""; // same-origin

function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, s => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[s]));
}

async function postJSON(path, body) {
  const res = await fetch(apiBase() + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {})
  });
  const text = await res.text();
  let json;
  try { json = JSON.parse(text); } catch { json = { raw: text }; }
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${JSON.stringify(json)}`);
  return json;
}

async function getJSON(path) {
  const res = await fetch(apiBase() + path, { method: 'GET' });
  const text = await res.text();
  let json;
  try { json = JSON.parse(text); } catch { json = { raw: text }; }
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${JSON.stringify(json)}`);
  return json;
}

function renderSchemaPreview(schema) {
  $('schemaOut').innerHTML = '<pre>' + escapeHtml(JSON.stringify(schema, null, 2)) + '</pre>';
}

function createFieldEl(field) {
  const wrap = document.createElement('div');
  wrap.className = 'field';

  const id = 'fld_' + field.name;
  const label = document.createElement('label');
  label.setAttribute('for', id);
  label.textContent = (field.label || field.name || 'Field') + (field.required ? ' *' : '');
  wrap.appendChild(label);

  let input;
  switch ((field.type || 'text')) {
    case 'textarea': {
      input = document.createElement('textarea');
      break;
    }
    case 'select': {
      input = document.createElement('select');
      const placeholderOpt = document.createElement('option');
      placeholderOpt.value = ''; placeholderOpt.textContent = 'Select...';
      input.appendChild(placeholderOpt);
      (field.options || []).forEach(o => {
        const opt = document.createElement('option');
        opt.value = String(o);
        opt.textContent = String(o);
        input.appendChild(opt);
      });
      break;
    }
    case 'checkbox': {
      input = document.createElement('input');
      input.type = 'checkbox';
      break;
    }
    case 'radio': {
      input = document.createElement('div');
      (field.options || []).forEach(o => {
        const lbl = document.createElement('label');
        const r = document.createElement('input');
        r.type = 'radio'; r.name = id; r.value = String(o);
        lbl.appendChild(r);
        lbl.appendChild(document.createTextNode(' ' + String(o)));
        input.appendChild(lbl);
        input.appendChild(document.createElement('br'));
      });
      break;
    }
    case 'email':
    case 'number':
    case 'date':
    case 'phone':
    case 'text':
    default: {
      input = document.createElement('input');
      input.type = field.type === 'phone' ? 'tel' : (field.type || 'text');
    }
  }

  if (input && input.tagName !== 'DIV') {
    input.id = id;
    if (field.placeholder) input.placeholder = field.placeholder;
  }
  wrap.appendChild(input);

  if (field.constraints && typeof field.constraints === 'object') {
    const hint = document.createElement('div');
    hint.className = 'hint';
    hint.textContent = 'Constraints: ' + JSON.stringify(field.constraints);
    wrap.appendChild(hint);
  }
  return wrap;
}

function renderForm(schema) {
  const form = $('dynamicForm');
  form.innerHTML = '';
  (schema.fields || []).forEach(f => form.appendChild(createFieldEl(f)));
}

function collectSubmission(schema) {
  const data = {};
  for (const f of (schema.fields || [])) {
    const id = 'fld_' + f.name;
    if (f.type === 'checkbox') {
      const el = document.getElementById(id);
      data[f.name] = !!(el && el.checked);
    } else if (f.type === 'radio') {
      const radios = document.getElementsByName(id);
      let chosen = '';
      Array.from(radios).forEach(r => { if (r.checked) chosen = r.value; });
      data[f.name] = chosen;
    } else {
      const el = document.getElementById(id);
      data[f.name] = el ? el.value : '';
    }
  }
  return data;
}

function renderValidation(result) {
  const block = $('validationBlock');
  block.innerHTML = '';
  const ok = result.valid;
  const status = document.createElement('div');
  status.className = ok ? 'ok' : 'fail';
  status.textContent = ok ? 'Looks good! ✅' : 'Please fix the issues below ❌';
  block.appendChild(status);

  if (!ok && result.errors && typeof result.errors === 'object') {
    const ul = document.createElement('ul');
    for (const [field, msg] of Object.entries(result.errors)) {
      const li = document.createElement('li');
      li.innerHTML = `<b>${escapeHtml(field)}</b>: ${escapeHtml(String(msg))}`;
      ul.appendChild(li);
    }
    block.appendChild(ul);
  }
}

async function refreshAnalytics() {
  if (!CURRENT_FORM_ID) return;
  const data = await getJSON(`/analytics/${CURRENT_FORM_ID}`);
  $('analyticsPre').textContent = JSON.stringify(data.insights || {}, null, 2);
  $('analyticsCount').textContent = `${data.total_submissions} submissions`;
}

function show(elementId, show = true) {
  $(elementId).style.display = show ? '' : 'none';
}

// ---- Event wiring ----
window.addEventListener('DOMContentLoaded', () => {
  $('btnGenerate').addEventListener('click', async () => {
    $('genStatus').textContent = 'Generating...';
    try {
      const body = { description: $('prompt').value || '' };
      if (!body.description.trim()) {
        $('genStatus').textContent = 'Please enter a description.';
        return;
      }
      const res = await postJSON('/create_form', body);
      CURRENT_FORM_ID = res.form_id;
      CURRENT_SCHEMA = res.schema || {};
      $('formMeta').textContent = `form_id: ${CURRENT_FORM_ID}`;
      $('formTitle').textContent = CURRENT_SCHEMA.title || 'Generated Form';
      renderSchemaPreview(CURRENT_SCHEMA);
      renderForm(CURRENT_SCHEMA);
      show('formCard', true);
      show('analyticsCard', true);
      $('genStatus').textContent = 'Done.';
      await refreshAnalytics();
    } catch (e) {
      $('genStatus').textContent = String(e.message || e);
    }
  });

  $('btnSubmit').addEventListener('click', async () => {
    if (!CURRENT_FORM_ID || !CURRENT_SCHEMA) return;
    $('submitStatus').textContent = 'Validating...';
    try {
      const submission = collectSubmission(CURRENT_SCHEMA);
      const res = await postJSON('/validate_submission', {
        form_id: CURRENT_FORM_ID,
        submission
      });
      renderValidation(res);
      $('submitStatus').textContent = res.valid ? 'Valid ✅' : 'Invalid ❌';
      await refreshAnalytics();
    } catch (e) {
      $('submitStatus').textContent = String(e.message || e);
    }
  });

  $('btnRecover').addEventListener('click', async () => {
    if (!CURRENT_FORM_ID || !CURRENT_SCHEMA) return;
    $('submitStatus').textContent = 'Recovering suggestions...';
    try {
      const submission = collectSubmission(CURRENT_SCHEMA);
      const res = await postJSON('/recover', {
        form_id: CURRENT_FORM_ID,
        submission
      });
      const block = $('validationBlock');
      const pre = document.createElement('pre');
      pre.textContent = JSON.stringify(res.suggestions || {}, null, 2);
      block.appendChild(pre);
      $('submitStatus').textContent = 'Suggestions ready.';
    } catch (e) {
      $('submitStatus').textContent = String(e.message || e);
    }
  });

  $('btnRefreshAnalytics').addEventListener('click', refreshAnalytics);
});
