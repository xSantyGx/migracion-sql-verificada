const form = document.getElementById('ask-form');
if (form) form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const answer = document.getElementById('answer');
  const button = form.querySelector('button');
  button.disabled = true;
  answer.textContent = 'Consultando evidencia…';
  try {
    const response = await fetch('/api/ask', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:form.question.value,run_id:form.dataset.run})});
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || 'No se pudo consultar.');
    answer.textContent = result.answer;
    for (const evidence of result.evidence || []) {
      const link = document.createElement('a');
      link.href = evidence.url;
      link.textContent = ` Ver procedimiento ${evidence.id} ↗`;
      answer.append(document.createElement('br'),link);
    }
  } catch (error) { answer.textContent = error.message; }
  finally { button.disabled = false; }
});
