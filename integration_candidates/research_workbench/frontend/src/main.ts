import { createApp } from 'vue';
import './style.css';
// Preserve the established stage UI as an explicit reference entry; saved-run
// mode never starts its live/workspace requests or downloads its large bundle.
const view = new URLSearchParams(window.location.search).get('view');
const app = view === 'research' ? import('./research-workbench/Root.vue')
  : view === 'legacy' ? import('./App.vue') : import('./views/SavedManagerResultView.vue');
app.then(({default: component}) => createApp(component).mount('#app'));
