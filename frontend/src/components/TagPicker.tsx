import { KeyboardEvent, useEffect, useMemo, useRef, useState } from 'react';

interface TagPickerProps {
  selectedTags: string[];
  availableTags: string[];
  onChange: (tags: string[]) => void;
}

export function TagPicker({ selectedTags, availableTags, onChange }: TagPickerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const allAvailableTags = useMemo(() => {
    const set = new Set([...availableTags, ...selectedTags]);
    return Array.from(set)
      .filter(Boolean)
      .sort((a, b) => a.localeCompare(b, 'de', { sensitivity: 'base' }));
  }, [availableTags, selectedTags]);

  const filteredTags = useMemo(() => {
    const query = inputValue.trim().toLowerCase();
    if (!query) return allAvailableTags;
    return allAvailableTags.filter((tag) => tag.toLowerCase().includes(query));
  }, [allAvailableTags, inputValue]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  function handleAddTag(tagToAdd: string) {
    const trimmed = tagToAdd.trim();
    if (!trimmed) return;
    const newTags = trimmed
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);
    const updated = Array.from(new Set([...selectedTags, ...newTags]));
    onChange(updated);
    setInputValue('');
  }

  function handleRemoveTag(tagToRemove: string) {
    onChange(selectedTags.filter((t) => t !== tagToRemove));
  }

  function handleToggleTag(tag: string) {
    if (selectedTags.includes(tag)) {
      handleRemoveTag(tag);
    } else {
      handleAddTag(tag);
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (inputValue.trim()) {
        handleAddTag(inputValue);
      }
    } else if (e.key === 'Backspace' && !inputValue && selectedTags.length > 0) {
      handleRemoveTag(selectedTags[selectedTags.length - 1]);
    } else if (e.key === 'Escape') {
      setIsOpen(false);
    }
  }

  const showCreateOption =
    inputValue.trim() !== '' &&
    !allAvailableTags.some((t) => t.toLowerCase() === inputValue.trim().toLowerCase());

  return (
    <div className="tag-picker" ref={containerRef}>
      <label className="tag-picker-label">
        Wähle Tags aus oder erstelle Neue (mit Enter bestätigen)
      </label>
      <div
        className={`tag-picker-input-container ${isOpen ? 'tag-picker-input-container--open' : ''}`}
        onClick={() => {
          setIsOpen(true);
          inputRef.current?.focus();
        }}
      >
        <div className="tag-picker-pills">
          {selectedTags.map((tag) => (
            <span key={tag} className="tag-picker-pill">
              {tag}
              <button
                type="button"
                className="tag-picker-pill-remove"
                aria-label={`Schlagwort ${tag} entfernen`}
                onClick={(e) => {
                  e.stopPropagation();
                  handleRemoveTag(tag);
                }}
              >
                ×
              </button>
            </span>
          ))}
          <input
            ref={inputRef}
            type="text"
            className="tag-picker-text-input"
            aria-label="Schlagwort eingeben"
            value={inputValue}
            onChange={(e) => {
              setInputValue(e.target.value);
              if (!isOpen) setIsOpen(true);
            }}
            onFocus={() => setIsOpen(true)}
            onKeyDown={handleKeyDown}
          />
        </div>
        <button
          type="button"
          className="tag-picker-toggle-button"
          aria-label={isOpen ? 'Schlagwörter-Menü schließen' : 'Schlagwörter-Menü öffnen'}
          onClick={(e) => {
            e.stopPropagation();
            setIsOpen((prev) => !prev);
          }}
        >
          {isOpen ? '▲' : '▼'}
        </button>

        {isOpen && (
          <div className="tag-picker-dropdown" role="listbox">
            {showCreateOption && (
              <div className="tag-picker-dropdown-create" onClick={() => handleAddTag(inputValue)}>
                + "{inputValue.trim()}" neu erstellen (Enter)
              </div>
            )}
            {filteredTags.length === 0 && !showCreateOption && (
              <div className="tag-picker-dropdown-empty">Keine Schlagwörter vorhanden</div>
            )}
            {filteredTags.map((tag) => {
              const isChecked = selectedTags.includes(tag);
              return (
                <label
                  key={tag}
                  className="tag-picker-dropdown-item"
                  onClick={(e) => e.stopPropagation()}
                >
                  <input
                    type="checkbox"
                    checked={isChecked}
                    onChange={() => handleToggleTag(tag)}
                  />
                  <span>{tag}</span>
                </label>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
