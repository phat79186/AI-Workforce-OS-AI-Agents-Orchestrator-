# Skill: Kubernetes Deployment

Deploy and manage applications on Kubernetes with best practices.

## Capabilities
- Deployment configurations
- Service definitions
- ConfigMaps and Secrets
- Horizontal Pod Autoscaler
- Health probes
- Resource management

## Patterns

### Complete Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: orchestrator
  labels:
    app: orchestrator
    version: v1
spec:
  replicas: 3
  selector:
    matchLabels:
      app: orchestrator
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: orchestrator
        version: v1
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000

      containers:
        - name: orchestrator
          image: orchestrator:latest
          imagePullPolicy: Always

          ports:
            - containerPort: 8000
              protocol: TCP

          env:
            - name: LOG_LEVEL
              valueFrom:
                configMapKeyRef:
                  name: orchestrator-config
                  key: log_level
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: orchestrator-secrets
                  key: database_url

          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"

          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 30
            timeoutSeconds: 5
            failureThreshold: 3

          readinessProbe:
            httpGet:
              path: /ready
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
            timeoutSeconds: 3
            failureThreshold: 3

          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop:
                - ALL

          volumeMounts:
            - name: data
              mountPath: /app/data
            - name: tmp
              mountPath: /tmp

      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: orchestrator-data
        - name: tmp
          emptyDir: {}

      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchLabels:
                    app: orchestrator
                topologyKey: kubernetes.io/hostname
```

### Service
```yaml
apiVersion: v1
kind: Service
metadata:
  name: orchestrator
  labels:
    app: orchestrator
spec:
  type: ClusterIP
  ports:
    - port: 80
      targetPort: 8000
      protocol: TCP
      name: http
  selector:
    app: orchestrator
```

### ConfigMap
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: orchestrator-config
data:
  log_level: "INFO"
  max_workers: "4"
  timeout_seconds: "300"
```

### Secrets
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: orchestrator-secrets
type: Opaque
stringData:
  database_url: "sqlite:///data/orchestrator.db"
  api_key: "your-api-key"
```

### Horizontal Pod Autoscaler
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: orchestrator-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: orchestrator
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Percent
          value: 100
          periodSeconds: 15
```

### Network Policy
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: orchestrator-network
spec:
  podSelector:
    matchLabels:
      app: orchestrator
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: api-gateway
      ports:
        - protocol: TCP
          port: 8000
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: database
      ports:
        - protocol: TCP
          port: 5432
```

## Checklist
- [ ] Resource requests and limits defined
- [ ] Liveness and readiness probes configured
- [ ] Security context set (non-root, read-only fs)
- [ ] HPA configured for auto-scaling
- [ ] Pod anti-affinity for high availability
- [ ] Network policies restrict traffic
- [ ] Secrets not in plain text
- [ ] Rolling update strategy configured
