chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'code-doctor-analyze',
    title: 'Analyze with Code Doctor',
    contexts: ['selection']
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== 'code-doctor-analyze') return;
  let code = info.selectionText || '';
  // selectionText collapses newlines; try to grab the real selection with line breaks
  try {
    const [res] = await chrome.scripting?.executeScript?.({
      target: { tabId: tab.id }, func: () => window.getSelection().toString()
    }) || [];
    if (res && res.result) code = res.result;
  } catch (e) { /* fall back to selectionText */ }
  await chrome.storage.local.set({ cd_code: code, cd_source: tab && tab.url || '' });
  chrome.tabs.create({ url: chrome.runtime.getURL('report.html') });
});
