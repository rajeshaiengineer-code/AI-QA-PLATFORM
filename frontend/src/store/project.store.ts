/**
 * Project Store — UI state for Project Management
 */

import { create } from "zustand";

import type { Project } from "@/types/project";

export interface ProjectFilters {
  page: number;
  page_size: number;
  organization_id: string;
  is_active: "" | "true" | "false";
  search: string;
}

interface ProjectState {
  filters: ProjectFilters;
  selectedProject: Project | null;
  isCreateOpen: boolean;
  isEditOpen: boolean;
  isDeleteOpen: boolean;
  setFilters: (patch: Partial<ProjectFilters>) => void;
  openCreate: () => void;
  closeCreate: () => void;
  openEdit: (project: Project) => void;
  closeEdit: () => void;
  openDelete: (project: Project) => void;
  closeDelete: () => void;
  setSelectedProject: (project: Project | null) => void;
}

const defaultFilters: ProjectFilters = {
  page: 1,
  page_size: 10,
  organization_id: "",
  is_active: "",
  search: "",
};

export const useProjectStore = create<ProjectState>((set) => ({
  filters: defaultFilters,
  selectedProject: null,
  isCreateOpen: false,
  isEditOpen: false,
  isDeleteOpen: false,
  setFilters: (patch) =>
    set((state) => ({ filters: { ...state.filters, ...patch } })),
  openCreate: () => set({ isCreateOpen: true }),
  closeCreate: () => set({ isCreateOpen: false }),
  openEdit: (project) =>
    set({ isEditOpen: true, selectedProject: project }),
  closeEdit: () => set({ isEditOpen: false }),
  openDelete: (project) =>
    set({ isDeleteOpen: true, selectedProject: project }),
  closeDelete: () => set({ isDeleteOpen: false }),
  setSelectedProject: (project) => set({ selectedProject: project }),
}));
