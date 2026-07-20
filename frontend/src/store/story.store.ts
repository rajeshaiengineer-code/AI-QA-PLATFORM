/**
 * Story Store — UI state for Story Management (filters, drawer, dialogs)
 */

import { create } from "zustand";

import type { Priority, Story, StoryStatus, StoryType } from "@/types/story";

export interface StoryFilters {
  search: string;
  status: StoryStatus | "";
  story_type: StoryType | "";
  priority: Priority | "";
  project_id: string;
  sprint_id: string;
  page: number;
  page_size: number;
}

interface StoryUiState {
  filters: StoryFilters;
  selectedStory: Story | null;
  isDrawerOpen: boolean;
  isCreateOpen: boolean;
  isEditOpen: boolean;
  isDeleteOpen: boolean;
  setFilters: (partial: Partial<StoryFilters>) => void;
  resetFilters: () => void;
  openDetails: (story: Story) => void;
  closeDrawer: () => void;
  openCreate: () => void;
  closeCreate: () => void;
  openEdit: (story: Story) => void;
  closeEdit: () => void;
  openDelete: (story: Story) => void;
  closeDelete: () => void;
}

const defaultFilters: StoryFilters = {
  search: "",
  status: "",
  story_type: "",
  priority: "",
  project_id: "",
  sprint_id: "",
  page: 1,
  page_size: 10,
};

export const useStoryStore = create<StoryUiState>((set) => ({
  filters: { ...defaultFilters },
  selectedStory: null,
  isDrawerOpen: false,
  isCreateOpen: false,
  isEditOpen: false,
  isDeleteOpen: false,

  setFilters: (partial) =>
    set((state) => ({
      filters: {
        ...state.filters,
        ...partial,
        // Reset to page 1 when filters other than page change
        page:
          partial.page !== undefined
            ? partial.page
            : Object.keys(partial).some((k) => k !== "page")
              ? 1
              : state.filters.page,
      },
    })),

  resetFilters: () => set({ filters: { ...defaultFilters } }),

  openDetails: (story) =>
    set({ selectedStory: story, isDrawerOpen: true }),

  closeDrawer: () => set({ isDrawerOpen: false }),

  openCreate: () => set({ isCreateOpen: true }),

  closeCreate: () => set({ isCreateOpen: false }),

  openEdit: (story) =>
    set({ selectedStory: story, isEditOpen: true, isDrawerOpen: false }),

  closeEdit: () => set({ isEditOpen: false }),

  openDelete: (story) =>
    set({ selectedStory: story, isDeleteOpen: true }),

  closeDelete: () => set({ isDeleteOpen: false }),
}));
