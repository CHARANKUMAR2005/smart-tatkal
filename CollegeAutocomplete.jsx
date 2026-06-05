import React, { useState, useEffect, useRef } from 'react';

const API_BASE = 'https://api.data.gov.in/resource/b9e8e2d9-ab1c-4e9b-8726-c7cee5efbd29';
const API_KEY = '579b464db66ec23bdd000001cdd3946e44ce4aab7b5b8a631f9ed8b4';

const FALLBACK_COLLEGES = [
  { universityname: 'Indian Institute of Technology Delhi', statename: 'Delhi' },
  { universityname: 'Indian Institute of Technology Bombay', statename: 'Maharashtra' },
  { universityname: 'Indian Institute of Technology Madras', statename: 'Tamil Nadu' },
  { universityname: 'Indian Institute of Technology Kanpur', statename: 'Uttar Pradesh' },
  { universityname: 'Indian Institute of Technology Kharagpur', statename: 'West Bengal' },
  { universityname: 'Indian Institute of Technology Roorkee', statename: 'Uttar Pradesh' },
  { universityname: 'Indian Institute of Technology Guwahati', statename: 'Assam' },
  { universityname: 'Indian Institute of Technology Hyderabad', statename: 'Telangana' },
  { universityname: 'Indian Institute of Technology Ropar', statename: 'Punjab' },
  { universityname: 'Indian Institute of Technology Indore', statename: 'Madhya Pradesh' },
  { universityname: 'National Institute of Technology Tiruchirappalli', statename: 'Tamil Nadu' },
  { universityname: 'National Institute of Technology Surathkal', statename: 'Karnataka' },
  { universityname: 'National Institute of Technology Warangal', statename: 'Telangana' },
  { universityname: 'National Institute of Technology Rourkela', statename: 'Odisha' },
  { universityname: 'National Institute of Technology Calicut', statename: 'Kerala' },
  { universityname: 'National Institute of Technology Durgapur', statename: 'West Bengal' },
  { universityname: 'National Institute of Technology Kurukshetra', statename: 'Haryana' },
  { universityname: 'National Institute of Technology Jamshedpur', statename: 'Jharkhand' },
  { universityname: 'National Institute of Technology Nagpur', statename: 'Maharashtra' },
  { universityname: 'Indian Institute of Management Ahmedabad', statename: 'Gujarat' },
  { universityname: 'Indian Institute of Management Bangalore', statename: 'Karnataka' },
  { universityname: 'Indian Institute of Management Calcutta', statename: 'West Bengal' },
  { universityname: 'Indian Institute of Management Lucknow', statename: 'Uttar Pradesh' },
  { universityname: 'Indian Institute of Science', statename: 'Karnataka' },
  { universityname: 'University of Delhi', statename: 'Delhi' },
  { universityname: 'Jawaharlal Nehru University', statename: 'Delhi' },
  { universityname: 'Banaras Hindu University', statename: 'Uttar Pradesh' },
  { universityname: 'University of Calcutta', statename: 'West Bengal' },
  { universityname: 'University of Madras', statename: 'Tamil Nadu' },
  { universityname: 'Anna University', statename: 'Tamil Nadu' },
  { universityname: 'University of Mumbai', statename: 'Maharashtra' },
  { universityname: 'Panjab University', statename: 'Punjab' },
  { universityname: 'University of Hyderabad', statename: 'Telangana' },
  { universityname: 'Jadavpur University', statename: 'West Bengal' },
  { universityname: 'Osmania University', statename: 'Telangana' },
  { universityname: 'Aligarh Muslim University', statename: 'Uttar Pradesh' },
  { universityname: 'Jamia Millia Islamia', statename: 'Delhi' },
  { universityname: 'St. Stephen’s College', statename: 'Delhi' },
  { universityname: 'Christ University', statename: 'Karnataka' },
  { universityname: 'Presidency University', statename: 'Karnataka' },
  { universityname: 'Vellore Institute of Technology', statename: 'Tamil Nadu' },
  { universityname: 'SRM Institute of Science and Technology', statename: 'Tamil Nadu' },
  { universityname: 'Manipal Academy of Higher Education', statename: 'Karnataka' },
  { universityname: 'Amrita Vishwa Vidyapeetham', statename: 'Tamil Nadu' },
  { universityname: 'National Law School of India University', statename: 'Karnataka' },
  { universityname: 'Indian Statistical Institute', statename: 'West Bengal' },
  { universityname: 'Birla Institute of Technology and Science Pilani', statename: 'Rajasthan' },
  { universityname: 'Jamia Millia Islamia', statename: 'Delhi' },
  { universityname: 'Symbiosis International University', statename: 'Maharashtra' },
  { universityname: 'Fergusson College', statename: 'Maharashtra' },
  { universityname: 'Loyola College', statename: 'Tamil Nadu' },
  { universityname: 'Madras Christian College', statename: 'Tamil Nadu' },
  { universityname: 'Xavier Institute of Management', statename: 'Jharkhand' },
  { universityname: 'Central University of Kerala', statename: 'Kerala' },
  { universityname: 'Central University of Rajasthan', statename: 'Rajasthan' },
  { universityname: 'National Institute of Technology Patna', statename: 'Bihar' },
  { universityname: 'National Institute of Technology Jalandhar', statename: 'Punjab' },
  { universityname: 'National Institute of Technology Allahabad', statename: 'Uttar Pradesh' },
  { universityname: 'Indian Institute of Management Kozhikode', statename: 'Kerala' },
  { universityname: 'Indian Institute of Management Shillong', statename: 'Meghalaya' },
];

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

  const normalizeCollege = (college) => ({
    ...college,
    universityname: college.universityname || college.college_name || college.name || '',
    statename: college.statename || college.state || '',
  });

  const matchesQuery = (college, value) => {
    const text = `${college.universityname || ''} ${college.statename || ''}`.toLowerCase();
    return text.includes(value.toLowerCase());
  };

  useEffect(() => {
    const trimmedQuery = query.trim();
    const fallback = FALLBACK_COLLEGES.filter((college) =>
      matchesQuery(college, trimmedQuery)
    );

    if (!trimmedQuery) {
      setResults([]);
      setNoResults(false);
      setLoading(false);
      return;
    }

    setLoading(true);
    setNoResults(false);

    window.clearTimeout(debounceTimer.current);
    debounceTimer.current = window.setTimeout(() => {
      fetch(
        `${API_BASE}?api-key=${API_KEY}&format=json&limit=50&filters[universityname][ilike]=${encodeURIComponent(
          trimmedQuery
        )}`
      )
        .then((response) => response.json())
        .then((data) => {
          const records = Array.isArray(data.records) ? data.records.map(normalizeCollege) : [];
          const finalResults = records.length > 0 ? records : fallback;
          setResults(finalResults);
          setNoResults(finalResults.length === 0);
          setOpen(true);
          setHighlightedIndex(-1);
        })
        .catch(() => {
          setResults(fallback);
          setNoResults(fallback.length === 0);
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

  const handleSelect = (collegeName) => {
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
        handleSelect(results[highlightedIndex].universityname || '');
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
          placeholder="Type to search..."
          style={{
            width: '100%',
            padding: '10px 36px 10px 12px',
            borderRadius: 6,
            border: '1px solid #ccc',
            outline: 'none',
            boxSizing: 'border-box',
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
            <div style={{ padding: '12px 14px', color: '#666' }}>No colleges found</div>
          ) : (
            results.map((college, index) => {
              const collegeName = college.universityname || '';
              const stateName = college.statename || '';
              const highlighted = index === highlightedIndex;
              return (
                <button
                  key={`${collegeName}-${index}`}
                  type="button"
                  onClick={() => handleSelect(collegeName)}
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
                  <div style={{ fontWeight: 700, color: '#1a1a1a' }}>{collegeName}</div>
                  <div style={{ fontSize: 13, color: '#777', marginTop: 4 }}>{stateName}</div>
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
