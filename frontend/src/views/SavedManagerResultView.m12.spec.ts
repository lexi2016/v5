import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,waitFor} from '@testing-library/vue';
import SavedManagerResultView from './SavedManagerResultView.vue';
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
it('M12 default-page button opens actual lazy saved content even when manager data is unavailable',async()=>{
 const fixture={schema_version:'v5.m12_saved_video.v1',module_id:'M12_VIDEO_FUPAN',status:'SAVED_ASR_REVIEW_REQUIRED',data_kind:'SYNTHETIC',research_only:true,natural_verified:false,review_completed:false,production_allowed:false,buy_gate_updated:false,orders_sent:false,reason_codes:['ASR_REVIEW_REQUIRED'],reference:{trade_date:'20261011',run_id:'synthetic',manifest_sha256:'a'.repeat(64),owner_receipt_sha256:'b'.repeat(64)},video:{title:'Synthetic M12 original video',target_trade_date:'20261011',asr_status:'ASR_REVIEW_REQUIRED',gap_status:'VIDEO_GAP_AUDIT_EMPTY'},transcript:{text:'Synthetic original transcript',sha256:'c'.repeat(64),truncated:false,total_characters:29},segments:{text:'0,1,SYNTHETIC',sha256:'d'.repeat(64),truncated:false,total_characters:13}};
 const calls:string[]=[];vi.stubGlobal('fetch',vi.fn(async(url:string)=>{calls.push(url);return url.startsWith('/api/v5/source-bundle/video-fupan')?new Response(JSON.stringify(fixture)):new Response('{}',{status:503});}));
 const view=render(SavedManagerResultView);const source=view.container.querySelector<HTMLDetailsElement>('#source-module-content')!;
 expect(source.open).toBe(false);expect(calls.filter(x=>x.includes('/video-fupan'))).toHaveLength(0);
 await fireEvent.click(view.getByRole('button',{name:'视频复盘 · M12'}));
 const target=view.container.querySelector<HTMLDetailsElement>('#m12-saved-video')!;
 await waitFor(()=>expect(target.open).toBe(true));await waitFor(()=>expect(view.queryByTestId('m12-saved-content')).not.toBeNull());
 expect(document.activeElement).toBe(target.querySelector('summary'));expect(source.open).toBe(false);expect(view.container.textContent).toContain('Synthetic original transcript');
 expect(view.getByRole('button',{name:'研究情报 · M04'})).toBeTruthy();expect(view.container.querySelector('#saved-result-content')).toBeTruthy();
});
