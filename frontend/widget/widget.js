const askButton = document.getElementById('ask');
const clearButton = document.getElementById('clear');
const answerEl = document.getElementById('answer');
const metaEl = document.getElementById('meta');
const helpfulBtn = document.getElementById('helpful');
const notHelpfulBtn = document.getElementById('notHelpful');
const feedbackStatusEl = document.getElementById('feedbackStatus');

let lastQueryMeta = null;
let lastCitations = [];

function setMeta(meta) {
  if (!meta) {
    metaEl.innerHTML = '';
    return;
  }
  const pills = [
    `city:${meta.city_id || ''}`,
    `model:${meta.model || ''}`,
    `k:${meta.retrieved_k ?? ''}`,
    meta.refused ? 'refused' : 'answered'
  ];
  metaEl.innerHTML = pills
    .filter(Boolean)
    .map(p => `<span class="pill">${p}</span>`)
    .join('');
}

function appendCitations(citations) {
  if (!citations || citations.length === 0) return;
  const lines = citations.map(c => `- ${c.title} (${c.uri})`);
  answerEl.textContent += `\n\nSources:\n${lines.join('\n')}`;
}

async function readSSE(response, onEvent) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buffer.indexOf('\n\n')) !== -1) {
      const raw = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      const lines = raw.split('\n');
      let event = 'message';
      let dataStr = '';
      for (const line of lines) {
        if (line.startsWith('event:')) event = line.slice(6).trim();
        if (line.startsWith('data:')) dataStr += line.slice(5).trim();
      }
      if (!dataStr) continue;
      try {
        onEvent(event, JSON.parse(dataStr));
      } catch (_) {
        // ignore malformed lines
      }
    }
  }
}

async function runQuery() {
  const cityId = document.getElementById('city').value.trim();
  const query = document.getElementById('query').value.trim();
  const stream = document.getElementById('stream').checked;

  answerEl.textContent = 'Thinking...';
  feedbackStatusEl.textContent = '';
  lastQueryMeta = null;
  lastCitations = [];
  setMeta(null);

  if (!cityId || !query) {
    answerEl.textContent = 'City ID and question are required.';
    return;
  }

  if (!stream) {
    try {
      const res = await fetch('http://localhost:8000/v1/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ city_id: cityId, query })
      });
      const data = await res.json();
      lastQueryMeta = data.meta || null;
      lastCitations = data.citations || [];
      setMeta(lastQueryMeta);
      answerEl.textContent = data.answer || '';
      appendCitations(lastCitations);
    } catch (err) {
      answerEl.textContent = `Request failed: ${err}`;
    }
    return;
  }

  try {
    const res = await fetch('http://localhost:8000/v1/query/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ city_id: cityId, query })
    });

    answerEl.textContent = '';
    await readSSE(res, (event, data) => {
      if (event === 'meta') {
        lastQueryMeta = data;
        lastCitations = data.citations || [];
        setMeta(data);
      } else if (event === 'token') {
        answerEl.textContent += data.token || '';
      } else if (event === 'done') {
        appendCitations(lastCitations);
      } else if (event === 'error') {
        answerEl.textContent = data.error || 'Streaming error.';
      }
    });
  } catch (err) {
    answerEl.textContent = `Request failed: ${err}`;
  }
}

async function submitFeedback(helpful) {
  if (!lastQueryMeta?.query_id) {
    feedbackStatusEl.textContent = 'Ask a question first.';
    return;
  }

  const cityId = document.getElementById('city').value.trim();
  const reason = document.getElementById('reason').value.trim() || null;

  try {
    const res = await fetch('http://localhost:8000/v1/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        city_id: cityId,
        query_id: lastQueryMeta.query_id,
        helpful,
        reason,
        escalation_requested: !helpful
      })
    });
    const data = await res.json();
    feedbackStatusEl.textContent = `Feedback saved (${data.feedback_id}).`;
  } catch (err) {
    feedbackStatusEl.textContent = `Feedback failed: ${err}`;
  }
}

askButton.addEventListener('click', runQuery);
clearButton.addEventListener('click', () => {
  answerEl.textContent = 'Waiting for your question...';
  feedbackStatusEl.textContent = '';
  lastQueryMeta = null;
  lastCitations = [];
  setMeta(null);
});
helpfulBtn.addEventListener('click', () => submitFeedback(true));
notHelpfulBtn.addEventListener('click', () => submitFeedback(false));
