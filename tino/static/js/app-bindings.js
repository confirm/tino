/**
 * Toolbar, tab bar, theme toggle, and panel resize event bindings.
 * Extracted from TinoApp to keep app.js within the line limit.
 */

const bindBucketSelect = app => {
  app.els.bucketBtn.addEventListener(
    'click',
    () => app.fileTree.openBucketPicker(),
  )
}

const bindFileButtons = app => {
  document.getElementById('btn-new')
    .addEventListener('click', () => {
      app.editor.createNewFile()
    })
  document.getElementById('btn-new-folder')
    .addEventListener('click', () => {
      app.fileTree.actions.createFolder()
    })
  document.getElementById('btn-template')
    .addEventListener('click', () => {
      app.templatePicker.open()
    })
  document.getElementById('btn-save')
    .addEventListener('click', () => {
      app.editor.saveCurrentFile()
    })
  document.getElementById('btn-fonts')
    .addEventListener('click', () => {
      app.fontManager.open()
    })
}

const bindDownloadButton = app => {
  document.getElementById('btn-download')
    .addEventListener('click', () => {
      if (!app.bucket)
        return
      const slug = encodeURIComponent(app.bucket)
      const link = document.createElement('a')
      link.href = `/api/buckets/${slug}/files/download`
      link.download = ''
      link.click()
    })
}

const bindGitButtons = app => {
  document.getElementById('btn-commit')
    .addEventListener('click', () => {
      app.git.openDialog()
    })
  document.getElementById('btn-commit-submit')
    .addEventListener('click', () => {
      app.git.submit()
    })
  document.getElementById('btn-commit-cancel')
    .addEventListener('click', () => {
      app.git.closeDialog()
    })
  app.els.commitDialog.addEventListener('click', evt => {
    if (evt.target === app.els.commitDialog)
      app.git.closeDialog()
  })
  app.els.commitFiles.addEventListener('click', evt => {
    const name = evt.target.closest('.commit-file-name')
    if (!name)
      return
    const li = name.closest('.commit-file-item')
    if (li && li.dataset.file)
      app.git.showDiffFor(li.dataset.file)
  })
  app.git.history.bind()
}

const bindThemeToggle = () => {
  const target = document.documentElement
  const saved = localStorage.getItem('tino:theme')
  if (saved)
    target.setAttribute('data-theme', saved)
  document.getElementById('btn-theme')
    .addEventListener('click', () => {
      const current = target.getAttribute('data-theme')
      const next = current === 'dark' ? 'light' : 'dark'
      target.setAttribute('data-theme', next)
      localStorage.setItem('tino:theme', next)
    })
}

const bindVimToggle = app => {
  const btn = document.getElementById('btn-vim')
  const enabled = localStorage.getItem('tino:vim') === 'on'
  app.els.editor.setVim(enabled)
  btn.classList.toggle('active', enabled)
  btn.addEventListener('click', () => {
    const next = !btn.classList.contains('active')
    app.els.editor.setVim(next)
    btn.classList.toggle('active', next)
    localStorage.setItem('tino:vim', next ? 'on' : 'off')
  })
}

const bindTabBar = app => {
  app.els.tabBar.addEventListener('click', evt => {
    const closeBtn = evt.target.closest('.tab-close')
    if (closeBtn) {
      const tab = closeBtn.closest('.tab')
      app.editor.closeTab(tab.dataset.file)
      return
    }
    const tab = evt.target.closest('.tab')
    if (tab)
      app.editor.openFile(tab.dataset.file)
  })
  document.getElementById('btn-close-all-tabs')
    .addEventListener('click', () => app.editor.closeAllTabs())
}

const bindLogout = () => {
  document.getElementById('btn-logout')
    .addEventListener('click', () => {
      window.location.href = '/logout'
    })
}

const bindPanelResize = app => {
  const fileExplorer = document.getElementById('file-explorer')
  const previewPanel = document.getElementById('preview-panel')
  app.panelResize.init('resize-left', () => fileExplorer, 'left')
  app.panelResize.init('resize-right', () => previewPanel, 'right')
}

/** Bind all toolbar buttons, tab bar, theme toggle, and panel resize. */

export const bindToolbar = app => {
  bindBucketSelect(app)
  bindFileButtons(app)
  bindDownloadButton(app)
  bindGitButtons(app)
  bindThemeToggle()
  bindVimToggle(app)
  bindTabBar(app)
  bindLogout()
  bindPanelResize(app)
}
