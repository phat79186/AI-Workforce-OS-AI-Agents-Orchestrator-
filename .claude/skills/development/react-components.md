# Skill: React Component Development

Build production-ready React components with TypeScript, hooks, and modern patterns.

## Capabilities
- Functional components with TypeScript
- Custom hooks for reusable logic
- Context API for state management
- Performance optimization (memo, useMemo, useCallback)
- Form handling with validation
- Error boundaries

## Patterns

### Component Structure
```tsx
interface ComponentProps {
  title: string;
  onAction: (id: string) => void;
  children?: React.ReactNode;
}

export const Component: React.FC<ComponentProps> = memo(({
  title,
  onAction,
  children
}) => {
  const [state, setState] = useState<State>(initialState);

  const handleClick = useCallback((id: string) => {
    onAction(id);
  }, [onAction]);

  return (
    <div className="component" role="region" aria-label={title}>
      <h2>{title}</h2>
      {children}
    </div>
  );
});

Component.displayName = 'Component';
```

### Custom Hook
```tsx
function useAsync<T>(asyncFn: () => Promise<T>, deps: DependencyList) {
  const [state, setState] = useState<{
    loading: boolean;
    error: Error | null;
    data: T | null;
  }>({ loading: true, error: null, data: null });

  useEffect(() => {
    let mounted = true;
    setState(s => ({ ...s, loading: true }));

    asyncFn()
      .then(data => mounted && setState({ loading: false, error: null, data }))
      .catch(error => mounted && setState({ loading: false, error, data: null }));

    return () => { mounted = false; };
  }, deps);

  return state;
}
```

## Checklist
- [ ] Props interface defined with TypeScript
- [ ] Accessibility attributes (role, aria-*)
- [ ] Error boundary wrapping critical sections
- [ ] Loading and error states handled
- [ ] Memoization for expensive computations
- [ ] Cleanup in useEffect
