document.getElementById('go').addEventListener('click', async () => {
  const code = document.getElementById('code').value;
  if (!code.trim()) return;
  await chrome.storage.local.set({ cd_code: code, cd_source: 'popup' });
  chrome.tabs.create({ url: chrome.runtime.getURL('report.html') });
});
