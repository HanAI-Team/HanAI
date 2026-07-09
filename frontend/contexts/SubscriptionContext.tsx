"use client";
import { createContext, useContext } from "react";

export const SubscriptionContext = createContext<boolean>(false);

export const useIsExpired = () => useContext(SubscriptionContext);
