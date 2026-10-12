import { createApp } from 'vue';
import '../style.css';
const view = new URLSearchParams(window.location.search).get('view');
const app = view === 'legacy' ? import('../views/ManagerSelectionView.vue') : import('../views/SavedManagerResultView.vue');
app.then(({default: component}) => createApp(component).mount('#manager-selection'));
