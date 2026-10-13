import type {M14SavedRebound, M14SavedWaiting, M14SavedEntry, M14SavedReference, M14ReboundGroup} from '../src/api/m14SavedRebound';
export const flags: {research_only: true; production_allowed: false; buy_gate_updated: false; orders_sent: false; natural_verified: false; formal_eligibility_verified: false};
export const reference: M14SavedReference;
export const counts: Record<M14ReboundGroup, number>;
export function entry(index: number, value?: unknown): M14SavedEntry;
export function saved(group?: M14ReboundGroup, offset?: number, total?: number): M14SavedRebound;
export function waiting(): M14SavedWaiting;
