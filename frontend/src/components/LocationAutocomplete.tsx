import { useState, useEffect, useRef, useCallback } from 'react';
import type { ChangeEvent, KeyboardEvent } from 'react';
import { MapPin, Navigation, X, Loader2, Compass } from 'lucide-react';
import { fetchPlaceSuggestions } from '../services/api';
import type { PlaceSuggestion } from '../types';

interface LocationAutocompleteProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  required?: boolean;
  icon?: 'origin' | 'destination';
}

function highlightMatch(text: string, query: string) {
  if (!query.trim()) return text;
  const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
  const parts = text.split(regex);
  return parts.map((part, index) =>
    regex.test(part) ? (
      <span key={index} className="autocomplete-match">
        {part}
      </span>
    ) : (
      part
    )
  );
}

export default function LocationAutocomplete({
  label,
  value,
  onChange,
  placeholder = 'City, address or ZIP',
  required = false,
  icon = 'origin',
}: LocationAutocompleteProps) {
  const [suggestions, setSuggestions] = useState<PlaceSuggestion[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const [isFocused, setIsFocused] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Fetch suggestions with debounce
  const fetchSuggestions = useCallback((query: string) => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const clean = query.trim();
    if (clean.length < 2) {
      setSuggestions([]);
      setIsOpen(false);
      setLoading(false);
      return;
    }

    setLoading(true);
    const controller = new AbortController();
    abortControllerRef.current = controller;

    fetchPlaceSuggestions(clean, controller.signal)
      .then(results => {
        setSuggestions(results);
        setIsOpen(results.length > 0);
        setHighlightedIndex(-1);
      })
      .catch(err => {
        if (err.name !== 'CanceledError' && err.code !== 'ERR_CANCELED') {
          setSuggestions([]);
        }
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const handleInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    onChange(newValue);
    fetchSuggestions(newValue);
  };

  const handleSelect = (suggestion: PlaceSuggestion) => {
    onChange(suggestion.place_name);
    setIsOpen(false);
    setSuggestions([]);
    setHighlightedIndex(-1);
  };

  const handleClear = () => {
    onChange('');
    setSuggestions([]);
    setIsOpen(false);
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (!isOpen || suggestions.length === 0) {
      if (e.key === 'ArrowDown' && suggestions.length > 0) {
        setIsOpen(true);
        e.preventDefault();
      }
      return;
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setHighlightedIndex(prev => (prev < suggestions.length - 1 ? prev + 1 : 0));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setHighlightedIndex(prev => (prev > 0 ? prev - 1 : suggestions.length - 1));
        break;
      case 'Enter':
        if (highlightedIndex >= 0 && highlightedIndex < suggestions.length) {
          e.preventDefault();
          e.stopPropagation();
          handleSelect(suggestions[highlightedIndex]);
        }
        break;
      case 'Escape':
        e.preventDefault();
        setIsOpen(false);
        break;
      case 'Tab':
        setIsOpen(false);
        break;
    }
  };

  // Close when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const listId = `suggestions-${label.toLowerCase().replace(/\s+/g, '-')}`;

  return (
    <div className="location-autocomplete-container" ref={containerRef}>
      <label className="field">
        <span>{label}</span>
        <div className={`input-wrap autocomplete-input-wrap ${isFocused ? 'focused' : ''}`}>
          <span className="field-icon">
            {icon === 'origin' ? <MapPin size={17} /> : <Navigation size={17} />}
          </span>
          <input
            ref={inputRef}
            type="text"
            value={value}
            onChange={handleInputChange}
            onFocus={() => {
              setIsFocused(true);
              if (value.trim().length >= 2 && suggestions.length > 0) {
                setIsOpen(true);
              } else if (value.trim().length >= 2) {
                fetchSuggestions(value);
              }
            }}
            onBlur={() => setIsFocused(false)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            required={required}
            autoComplete="off"
            autoCorrect="off"
            spellCheck="false"
            aria-autocomplete="list"
            aria-controls={listId}
            aria-expanded={isOpen}
          />
          {loading && (
            <span className="input-action-spinner" title="Loading suggestions...">
              <Loader2 size={15} className="spin" />
            </span>
          )}
          {!loading && value && (
            <button
              type="button"
              className="input-clear-btn"
              onClick={handleClear}
              title="Clear location"
              tabIndex={-1}
            >
              <X size={15} />
            </button>
          )}
        </div>
      </label>

      {isOpen && suggestions.length > 0 && (
        <ul className="autocomplete-dropdown" id={listId} role="listbox">
          <li className="autocomplete-dropdown-header">
            <span>SUGGESTED LOCATIONS</span>
            <span className="provider-tag">GOOGLE MAPS STYLE</span>
          </li>
          {suggestions.map((suggestion, index) => {
            const isHighlighted = index === highlightedIndex;
            return (
              <li
                key={suggestion.id || `${suggestion.place_name}-${index}`}
                role="option"
                aria-selected={isHighlighted}
                className={`autocomplete-item ${isHighlighted ? 'active' : ''}`}
                onMouseDown={e => {
                  // Prevent blur before selection
                  e.preventDefault();
                  handleSelect(suggestion);
                }}
                onMouseEnter={() => setHighlightedIndex(index)}
              >
                <div className="autocomplete-item-icon">
                  <Compass size={15} />
                </div>
                <div className="autocomplete-item-content">
                  <div className="autocomplete-primary">
                    {highlightMatch(suggestion.primary_text, value)}
                  </div>
                  {suggestion.secondary_text && (
                    <div className="autocomplete-secondary">{suggestion.secondary_text}</div>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

