'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { UnitSystem } from './units';

interface StoreContextType {
  unitSystem: UnitSystem;
  setUnitSystem: (system: UnitSystem) => void;
  toggleUnitSystem: () => void;
  
  // Comparison
  comparisonIds: string[];
  addToCompare: (id: string) => boolean;
  removeFromCompare: (id: string) => void;
  toggleCompare: (id: string) => void;
  clearCompare: () => void;
  isInCompare: (id: string) => boolean;

  // Favourites
  favourites: string[];
  toggleFavourite: (id: string) => void;
  isFavourite: (id: string) => boolean;

  // Recently Viewed
  recentlyViewed: string[];
  addRecentlyViewed: (id: string) => void;

  // Search Modal
  isSearchOpen: boolean;
  setIsSearchOpen: (open: boolean) => void;
}

const StoreContext = createContext<StoreContextType | undefined>(undefined);

export function StoreProvider({ children }: { children: React.ReactNode }) {
  const [unitSystem, setUnitSystem] = useState<UnitSystem>('metric');
  const [comparisonIds, setComparisonIds] = useState<string[]>([]);
  const [favourites, setFavourites] = useState<string[]>([]);
  const [recentlyViewed, setRecentlyViewed] = useState<string[]>([]);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [mounted, setMounted] = useState(false);

  // Load from LocalStorage
  useEffect(() => {
    try {
      const savedUnit = localStorage.getItem('autoverse_unit') as UnitSystem;
      if (savedUnit === 'metric' || savedUnit === 'imperial') {
        setUnitSystem(savedUnit);
      }

      const savedCompare = localStorage.getItem('autoverse_compare');
      if (savedCompare) {
        setComparisonIds(JSON.parse(savedCompare));
      }

      const savedFavs = localStorage.getItem('autoverse_favourites');
      if (savedFavs) {
        setFavourites(JSON.parse(savedFavs));
      }

      const savedRecent = localStorage.getItem('autoverse_recent');
      if (savedRecent) {
        setRecentlyViewed(JSON.parse(savedRecent));
      }
    } catch (e) {
      console.warn('LocalStorage access warning:', e);
    }
    setMounted(true);
  }, []);

  // Save changes to localStorage
  const handleSetUnit = (system: UnitSystem) => {
    setUnitSystem(system);
    try {
      localStorage.setItem('autoverse_unit', system);
    } catch (e) {}
  };

  const toggleUnitSystem = () => {
    handleSetUnit(unitSystem === 'metric' ? 'imperial' : 'metric');
  };

  const addToCompare = (id: string): boolean => {
    if (comparisonIds.includes(id)) return true;
    if (comparisonIds.length >= 4) {
      alert('You can compare a maximum of 4 vehicles at a time. Remove one first.');
      return false;
    }
    const updated = [...comparisonIds, id];
    setComparisonIds(updated);
    try {
      localStorage.setItem('autoverse_compare', JSON.stringify(updated));
    } catch (e) {}
    return true;
  };

  const removeFromCompare = (id: string) => {
    const updated = comparisonIds.filter(i => i !== id);
    setComparisonIds(updated);
    try {
      localStorage.setItem('autoverse_compare', JSON.stringify(updated));
    } catch (e) {}
  };

  const toggleCompare = (id: string) => {
    if (comparisonIds.includes(id)) {
      removeFromCompare(id);
    } else {
      addToCompare(id);
    }
  };

  const clearCompare = () => {
    setComparisonIds([]);
    try {
      localStorage.removeItem('autoverse_compare');
    } catch (e) {}
  };

  const isInCompare = (id: string) => comparisonIds.includes(id);

  const toggleFavourite = (id: string) => {
    const updated = favourites.includes(id) 
      ? favourites.filter(i => i !== id)
      : [...favourites, id];
    setFavourites(updated);
    try {
      localStorage.setItem('autoverse_favourites', JSON.stringify(updated));
    } catch (e) {}
  };

  const isFavourite = (id: string) => favourites.includes(id);

  const addRecentlyViewed = (id: string) => {
    const filtered = recentlyViewed.filter(i => i !== id);
    const updated = [id, ...filtered].slice(0, 8);
    setRecentlyViewed(updated);
    try {
      localStorage.setItem('autoverse_recent', JSON.stringify(updated));
    } catch (e) {}
  };

  return (
    <StoreContext.Provider
      value={{
        unitSystem,
        setUnitSystem: handleSetUnit,
        toggleUnitSystem,
        comparisonIds,
        addToCompare,
        removeFromCompare,
        toggleCompare,
        clearCompare,
        isInCompare,
        favourites,
        toggleFavourite,
        isFavourite,
        recentlyViewed,
        addRecentlyViewed,
        isSearchOpen,
        setIsSearchOpen,
      }}
    >
      {children}
    </StoreContext.Provider>
  );
}

export function useStore() {
  const context = useContext(StoreContext);
  if (!context) {
    throw new Error('useStore must be used within a StoreProvider');
  }
  return context;
}
