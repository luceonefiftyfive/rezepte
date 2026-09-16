import { useEffect, useRef, useState } from 'react';

interface GroupOption {
  id: string;
  name: string;
}

interface GroupPickerProps {
  selectedGroupIds: string[];
  availableGroups: GroupOption[];
  onChange: (groupIds: string[]) => void;
  onValidationError?: (message: string) => void;
}

export function GroupPicker({
  selectedGroupIds,
  availableGroups,
  onChange,
  onValidationError,
}: GroupPickerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  function toggleGroup(groupId: string) {
    if (selectedGroupIds.includes(groupId)) {
      // at least one recipe book must stay selected
      if (selectedGroupIds.length === 1) {
        onValidationError?.('Bitte mindestens ein Rezeptbuch auswählen.');
        return;
      }
      onChange(selectedGroupIds.filter((id) => id !== groupId));
      return;
    }
    onValidationError?.('');
    onChange([...selectedGroupIds, groupId]);
  }

  const selectedGroups = availableGroups.filter((group) => selectedGroupIds.includes(group.id));

  return (
    <div className="tag-picker" ref={containerRef}>
      <label className="tag-picker-label" title="Mindestens ein Rezeptbuch ist erforderlich.">
        Rezeptbücher
      </label>
      <div
        className={`tag-picker-input-container ${isOpen ? 'tag-picker-input-container--open' : ''}`}
        onClick={() => setIsOpen(true)}
      >
        <div className="tag-picker-pills">
          {selectedGroups.length === 0 && (
            <span className="tag-picker-placeholder">Keine Rezeptbücher ausgewählt</span>
          )}
          {selectedGroups.map((group) => (
            <span key={group.id} className="tag-picker-pill">
              {group.name}
              <button
                type="button"
                className="tag-picker-pill-remove"
                aria-label={`Rezeptbuch ${group.name} entfernen`}
                onClick={(e) => {
                  e.stopPropagation();
                  toggleGroup(group.id);
                }}
              >
                ×
              </button>
            </span>
          ))}
        </div>
        <button
          type="button"
          className="tag-picker-toggle-button"
          aria-label={isOpen ? 'Rezeptbücher-Menü schließen' : 'Rezeptbücher-Menü öffnen'}
          title="Mindestens ein Rezeptbuch ist erforderlich."
          onClick={(e) => {
            e.stopPropagation();
            setIsOpen((prev) => !prev);
          }}
        >
          {isOpen ? '▲' : '▼'}
        </button>

        {isOpen && (
          <div className="tag-picker-dropdown" role="listbox">
            {availableGroups.map((group) => (
              <label
                key={group.id}
                className="tag-picker-dropdown-item"
                onClick={(e) => e.stopPropagation()}
              >
                <input
                  type="checkbox"
                  checked={selectedGroupIds.includes(group.id)}
                  onChange={() => toggleGroup(group.id)}
                />
                <span>{group.name}</span>
              </label>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
