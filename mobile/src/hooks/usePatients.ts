import { useInfiniteQuery } from "@tanstack/react-query";
import { getPatients } from "../api/patients";

export function usePatients(search: string) {
  return useInfiniteQuery({
    queryKey: ["patients", search],
    queryFn: ({ pageParam }) => getPatients(pageParam, search || undefined),
    initialPageParam: 1,
    getNextPageParam: (lastPage) => {
      const loaded = lastPage.page * lastPage.size;
      return loaded < lastPage.total ? lastPage.page + 1 : undefined;
    },
  });
}
