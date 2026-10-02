import { describe, expect, it } from 'vitest';
import { SaveStatus } from '../types';

export interface AutosaveMachineState {
  currentRev: number;
  lastSavedSceneVersion: number;
  status: SaveStatus;
  isDirty: boolean;
  errorMessage: string | null;
}

export function createAutosaveMachine(initialRev = 0, initialSceneVersion = 0): {
  getState: () => AutosaveMachineState;
  onCanvasChange: (newSceneVersion: number) => boolean; // returns true if save needed
  onSaveStart: () => void;
  onSaveSuccess: (newRev: number, savedSceneVersion: number) => void;
  onSaveConflict: (message?: string) => void;
  onSaveError: (error: string) => void;
} {
  let state: AutosaveMachineState = {
    currentRev: initialRev,
    lastSavedSceneVersion: initialSceneVersion,
    status: 'saved',
    isDirty: false,
    errorMessage: null,
  };

  return {
    getState: () => ({ ...state }),

    onCanvasChange: (newSceneVersion: number) => {
      if (newSceneVersion === state.lastSavedSceneVersion) {
        return false;
      }
      state.isDirty = true;
      return true;
    },

    onSaveStart: () => {
      state.status = 'saving';
      state.errorMessage = null;
    },

    onSaveSuccess: (newRev: number, savedSceneVersion: number) => {
      state.currentRev = newRev;
      state.lastSavedSceneVersion = savedSceneVersion;
      state.status = 'saved';
      state.isDirty = false;
      state.errorMessage = null;
    },

    onSaveConflict: (message = 'Conflict') => {
      state.status = 'conflict';
      state.errorMessage = message;
    },

    onSaveError: (error: string) => {
      state.status = 'error';
      state.errorMessage = error;
    },
  };
}

describe('Autosave State Machine', () => {
  it('detects changes when scene version changes and ignores unchanged version', () => {
    const machine = createAutosaveMachine(0, 100);

    // Pan / zoom changes (scene version stays 100)
    const needed1 = machine.onCanvasChange(100);
    expect(needed1).toBe(false);
    expect(machine.getState().isDirty).toBe(false);

    // Real element modification (version becomes 101)
    const needed2 = machine.onCanvasChange(101);
    expect(needed2).toBe(true);
    expect(machine.getState().isDirty).toBe(true);
  });

  it('progresses from saving to saved on success and updates rev', () => {
    const machine = createAutosaveMachine(0, 100);
    machine.onCanvasChange(105);

    machine.onSaveStart();
    expect(machine.getState().status).toBe('saving');

    machine.onSaveSuccess(1, 105);
    const state = machine.getState();
    expect(state.status).toBe('saved');
    expect(state.currentRev).toBe(1);
    expect(state.lastSavedSceneVersion).toBe(105);
    expect(state.isDirty).toBe(false);
  });

  it('transitions to conflict on 409 stale revision response', () => {
    const machine = createAutosaveMachine(1, 100);
    machine.onCanvasChange(102);
    machine.onSaveStart();
    machine.onSaveConflict('Draft revision conflict');

    const state = machine.getState();
    expect(state.status).toBe('conflict');
    expect(state.errorMessage).toBe('Draft revision conflict');
  });

  it('transitions to error on network failure and preserves rev for retry', () => {
    const machine = createAutosaveMachine(2, 100);
    machine.onCanvasChange(103);
    machine.onSaveStart();
    machine.onSaveError('Network timeout');

    const state = machine.getState();
    expect(state.status).toBe('error');
    expect(state.errorMessage).toBe('Network timeout');
    expect(state.currentRev).toBe(2);
  });
});
