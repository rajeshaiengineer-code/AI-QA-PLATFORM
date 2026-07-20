/**
 * Sprint Store — UI state for Sprint Management
 */

import { create } from "zustand";

import type { Sprint } from "@/types/sprint";

export interface SprintFilters {
  page: number;
  page_size: number;
  project_id: string;
  is_active: "" | "true" | "false";
  search: string;
}

interface SprintState {
  filters: SprintFilters;
  selectedSprint: Sprint | null;
  isCreateOpen: boolean;
  isEditOpen: boolean;
  isDeleteOpen: boolean;
  setFilters: (patch: Partial<SprintFilters>) => void;
  openCreate: () => void;
  closeCreate: () => void;
  openEdit: (sprint: Sprint) => void;
  closeEdit: () => void;
  openDelete: (sprint: Sprint) => void;
  closeDelete: () => void;
}

const defaultFilters: SprintFilters = {
  page: 1,
  page_size: 10,
  project_id: "",
  is_active: "",
  search: "",
};

export const useSprintStore = create<SprintState>((set) => ({
  filters: defaultFilters,
  selectedSprint: null,
  isCreateOpen: false,
  isEditOpen: false,
  isDeleteOpen: false,
  setFilters: (patch) =>
    set((state) => ({ filters: { ...state.filters, ...patch } })),
  openCreate: () => set({ isCreateOpen: true }),
  closeCreate: () => set({ isCreateOpen: false }),
  openEdit: (sprint) => set({ isEditOpen: true, selectedSprint: sprint }),
  closeEdit: () => set({ isEditOpen: false }),
  openDelete: (sprint) => set({ isDeleteOpen: true, selectedSprint: sprint }),
  closeDelete: () => set({ isDeleteOpen: false }),
}));
