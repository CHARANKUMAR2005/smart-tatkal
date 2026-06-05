import React, { useState, useEffect, useRef } from 'react';

/**
 * CollegeAutocomplete Component - Django integrated version
 * Calls Django API endpoint at /accounts/api/colleges/search/
 * 
 * Usage: <CollegeAutocomplete onChange={(collegeName) => console.log(collegeName)} />
 * 
 * Props:
 *   - onChange: callback function when college is selected or cleared
 * 
 * Features:
 * - 300ms debounce on search queries
 * - Keyboard navigation (ArrowUp/Down, Enter, Escape)
 * - Click outside to close dropdown
 * - Clear button to reset selection
 * - Fetches from Django backend: /accounts/api/colleges/search/?q=query
 */

const CollegeAutocomplete = ({ onChange }) => {
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const [noResults, setNoResults] = useState(false);
  const debounceTimer = useRef(null);
  const containerRef = useRef(null);

  useEffect(() => {
    const trimmedQuery = query.trim();

    if (!trimmedQuery || trimmedQuery.length < 2) {
      setResults([]);
      setNoResults(false);
      setLoading(false);
      return;
    }

    setLoading(true);
    setNoResults(false);

    window.clearTimeout(debounceTimer.current);
    debounceTimer.current = window.setTimeout(() => {
      // Call Django API endpoint
      fetch(`/accounts/api/colleges/search/?q=${encodeURIComponent(trimmedQuery)}`)
        .then((response) => response.json())
        .then((data) => {
          const finalResults = Array.isArray(data) ? data : [];
          setResults(finalResults);
          setNoResults(finalResults.length === 0);
          setOpen(true);
          setHighlightedIndex(-1);
        })
        .catch((error) => {
          console.error('Error fetching colleges:', error);
          setResults([]);
          setNoResults(true);
          setOpen(true);
          setHighlightedIndex(-1);
        })
        .finally(() => setLoading(false));
    }, 300);

    return () => window.clearTimeout(debounceTimer.current);
  }, [query]);

  useEffect(() => {
    const onClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setOpen(false);
      }
    };

    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, []);

  const handleSelect = (college) => {
    const collegeName = college.name || college.display;
    setSelected(collegeName);
    setQuery(collegeName);
    setOpen(false);
    setResults([]);
    setHighlightedIndex(-1);
    setNoResults(false);
    if (onChange) onChange(collegeName);
  };

  const handleClear = () => {
    setSelected('');
    setQuery('');
    setResults([]);
    setOpen(false);
    setHighlightedIndex(-1);
    setNoResults(false);
    if (onChange) onChange('');
  };

  const handleKeyDown = (event) => {
    if (!open) {
      if (event.key === 'ArrowDown' && results.length > 0) {
        setOpen(true);
        setHighlightedIndex(0);
      }
      return;
    }

    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setHighlightedIndex((prev) => Math.min(prev + 1, results.length - 1));
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setHighlightedIndex((prev) => Math.max(prev - 1, 0));
    } else if (event.key === 'Enter') {
      event.preventDefault();
      if (highlightedIndex >= 0 && highlightedIndex < results.length) {
        handleSelect(results[highlightedIndex]);
      }
    } else if (event.key === 'Escape') {
      setOpen(false);
    }
  };

  return (
    <div style={{ position: 'relative', width: '100%', maxWidth: 420 }} ref={containerRef}>
      <label style={{ display: 'block', marginBottom: 8, fontWeight: 600 }}>
        University / College
      </label>

      <div style={{ position: 'relative' }}>
        <input
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setSelected('');
            setOpen(true);
          }}
          onKeyDown={handleKeyDown}
          placeholder="Type to search colleges..."
          style={{
            width: '100%',
            padding: '10px 36px 10px 12px',
            borderRadius: 6,
            border: '1px solid #ccc',
            outline: 'none',
            boxSizing: 'border-box',
            fontSize: '14px',
          }}
          aria-expanded={open}
          aria-haspopup="listbox"
        />
        {query && (
          <button
            type="button"
            onClick={handleClear}
            style={{
              position: 'absolute',
              right: 10,
              top: '50%',
              transform: 'translateY(-50%)',
              background: 'transparent',
              border: 'none',
              color: '#999',
              cursor: 'pointer',
              fontSize: 18,
              lineHeight: 1,
              padding: 0,
            }}
            aria-label="Clear"
          >
            ×
          </button>
        )}
      </div>

      {loading && (
        <div style={{ marginTop: 8, color: '#555', fontSize: 14 }}>
          Loading...
        </div>
      )}

      {open && (results.length > 0 || noResults) && (
        <div
          style={{
            position: 'absolute',
            top: 72,
            left: 0,
            right: 0,
            zIndex: 10,
            background: '#fff',
            border: '1px solid #ddd',
            borderRadius: 6,
            boxShadow: '0 8px 24px rgba(0,0,0,0.08)',
            maxHeight: 300,
            overflowY: 'auto',
          }}
          role="listbox"
        >
          {noResults ? (
            <div style={{ padding: '12px 14px', color: '#666', textAlign: 'center' }}>
              No colleges found
            </div>
          ) : (
            results.map((college, index) => {
              const collegeName = college.name || college.display || '';
              const state = college.state || '';
              const highlighted = index === highlightedIndex;
              return (
                <button
                  key={`${collegeName}-${state}-${index}`}
                  type="button"
                  onClick={() => handleSelect(college)}
                  onMouseEnter={() => setHighlightedIndex(index)}
                  style={{
                    display: 'block',
                    width: '100%',
                    textAlign: 'left',
                    padding: '12px 14px',
                    border: 'none',
                    background: highlighted ? '#f4f7ff' : '#fff',
                    cursor: 'pointer',
                  }}
                >
                  <div style={{ fontWeight: 700, color: '#1a1a1a', fontSize: '14px' }}>
                    {collegeName}
                  </div>
                  <div style={{ fontSize: 12, color: '#777', marginTop: 4 }}>
                    {state}
                  </div>
                </button>
              );
            })
          )}
        </div>
      )}
    </div>
  );
};

export default CollegeAutocomplete;
