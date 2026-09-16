import { useQuery } from "@tanstack/react-query";

import { api } from "./client";

export const useFlavorTags = () =>
  useQuery({ queryKey: ["flavor-tags"], queryFn: api.flavorTags, staleTime: Number.POSITIVE_INFINITY });

export const useBeans = (limit = 50) => useQuery({ queryKey: ["beans", limit], queryFn: () => api.beans(limit) });

export const useBean = (id: number) => useQuery({ queryKey: ["bean", id], queryFn: () => api.bean(id) });

export const useSimilarBeans = (id: number) =>
  useQuery({ queryKey: ["bean", id, "similar"], queryFn: () => api.similarBeans(id) });

export const useBrews = (params: { beanId?: number; limit?: number } = {}) =>
  useQuery({ queryKey: ["brews", params], queryFn: () => api.brews(params) });

export const useBrew = (id: number | undefined) =>
  useQuery({ queryKey: ["brew", id], queryFn: () => api.brew(id as number), enabled: id !== undefined });

export const useGrinders = () => useQuery({ queryKey: ["grinders"], queryFn: api.grinders });

export const useCalibration = (grinderId: number) =>
  useQuery({ queryKey: ["calibration", grinderId], queryFn: () => api.calibration(grinderId) });

export const useClickSuggestion = (grinderId: number, target: number | null) =>
  useQuery({
    queryKey: ["calibration", grinderId, "suggest", target],
    queryFn: () => api.suggestClicks(grinderId, target as number),
    enabled: target !== null && target > 0 && target <= 3,
  });

export const useCatalog = () => useQuery({ queryKey: ["catalog"], queryFn: () => api.catalog() });

export const useLatestRecommendations = () =>
  useQuery({ queryKey: ["recommendations", "latest"], queryFn: api.latestRecommendations });
