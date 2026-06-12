import { create } from 'zustand'

/** Mobile-only drawer state (left panel / contacts). Irrelevant on lg+ screens
 *  where both panels are always visible. */
interface UiState {
  leftDrawerOpen: boolean
  rightDrawerOpen: boolean
  toggleLeftDrawer: () => void
  toggleRightDrawer: () => void
  closeDrawers: () => void
}

export const useUiStore = create<UiState>((set) => ({
  leftDrawerOpen: false,
  rightDrawerOpen: false,
  toggleLeftDrawer: () =>
    set((s) => ({ leftDrawerOpen: !s.leftDrawerOpen, rightDrawerOpen: false })),
  toggleRightDrawer: () =>
    set((s) => ({ rightDrawerOpen: !s.rightDrawerOpen, leftDrawerOpen: false })),
  closeDrawers: () => set({ leftDrawerOpen: false, rightDrawerOpen: false }),
}))
