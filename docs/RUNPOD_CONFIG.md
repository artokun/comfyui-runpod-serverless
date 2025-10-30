# RunPod Endpoint Configuration Guide

Complete guide for optimizing your ComfyUI serverless endpoint on RunPod.

## Quick Configuration Templates

### Template 1: High-Volume Production (24/7)
**Use Case**: Constant traffic, minimal cold starts acceptable

```
Container Image: alongbottom/comfyui-runpod:latest
GPU Type: 48GB (L40S, A6000) + 24GB (A5000, RTX A5000) fallbacks
Container Disk: 30GB
Network Volume: Attach your models volume

Active Workers (Min): 2-3
Max Workers: 10
GPUs Per Worker: 1

Idle Timeout: 30 seconds
Execution Timeout: 600 seconds (adjust based on your workflows)

FlashBoot: Enabled
Data Centers: All available (unless using network volume)

Estimated Cost: ~$20-40/day for active workers
```

### Template 2: Moderate Traffic with Cost Optimization
**Use Case**: Intermittent traffic, balance cost vs. latency

```
Container Image: alongbottom/comfyui-runpod:latest
GPU Type: 24GB (A5000, RTX A5000) + 48GB fallback
Container Disk: 30GB
Network Volume: Attach your models volume

Active Workers (Min): 0
Max Workers: 5
GPUs Per Worker: 1

Idle Timeout: 10 seconds
Execution Timeout: 600 seconds

FlashBoot: Enabled
Scaling Type: Queue Delay
Delay Threshold: 6 seconds

Data Centers: All available (unless using network volume)

Estimated Cost: Pay-per-use (~$0.0003/sec active time)
```

### Template 3: Dev/Testing Environment
**Use Case**: Development, testing, low traffic

```
Container Image: alongbottom/comfyui-runpod:latest
GPU Type: 16GB (RTX 4090, A4000)
Container Disk: 20GB
Network Volume: Optional (can use smaller test volume)

Active Workers (Min): 0
Max Workers: 2
GPUs Per Worker: 1

Idle Timeout: 5 seconds
Execution Timeout: 300 seconds

FlashBoot: Enabled

Estimated Cost: <$5/day typical usage
```

## Detailed Configuration Options

### 1. Endpoint Type

**Queue-Based (Recommended for ComfyUI)**
- Asynchronous job processing
- Built-in retry logic
- Status polling
- Better for long-running workflows (>30s)

**Load Balancing**
- Synchronous HTTP requests
- Lower latency for quick requests
- Requires HTTP server in container (not our current setup)

**Choice**: Use **Queue-Based** for ComfyUI workflows.

### 2. GPU Selection Strategy

**For SDXL/FLUX Models**: 24GB minimum
- Primary: RTX A5000, A5000 (24GB)
- Fallback: L40S, A6000 (48GB)

**For SD 1.5 Models**: 16GB sufficient
- Primary: RTX 4090, A4000 (16GB)
- Fallback: A5000 (24GB)

**For Multiple Large Models**: 48GB+
- Primary: L40S, A6000 (48GB)
- Fallback: A100 (80GB) if budget allows

**Pro Tip**: Select multiple GPU types to increase availability, but order by cost efficiency.

### 3. Worker Configuration

#### Active (Min) Workers

**Formula**: `(Requests per Minute × Avg Request Duration in Seconds) / 60`

Examples:
- 10 req/min × 30s duration = 5 active workers
- 2 req/min × 60s duration = 2 active workers

**Benefits**:
- No cold starts
- 30% discount on pricing
- Consistent performance

**Cost**: ~$0.00020/sec × 60 × 60 × 24 = $17.28/day per worker (24GB GPU)

**When to Use**:
- Production with steady traffic
- SLA requirements for response time
- Can afford $15-50/day per worker

**When to Skip**:
- Low/intermittent traffic
- Dev/testing
- Budget constraints

#### Max Workers

**Formula**: `Expected Peak Concurrency × 1.2`

Examples:
- Expect 5 concurrent requests → Set max to 6
- Expect 20 concurrent requests → Set max to 24

**Pro Tips**:
- Start conservative, monitor, then increase
- Too high = wasted scaling capacity
- Too low = throttled requests during spikes

#### GPUs Per Worker

**Recommendation**: 1 GPU per worker

**Exceptions**:
- Multi-GPU parallel workflows (rare in ComfyUI)
- Extremely large models requiring >80GB VRAM

**Why 1 GPU?**:
- Better parallelization across workers
- Lower overhead
- More flexible scaling

### 4. Timeout Configuration

#### Idle Timeout

How long workers stay alive after completing a request.

**Short (5s)**:
- Cost optimized
- Suitable for sporadic traffic
- Cold starts more common

**Medium (30s)**:
- Balanced approach
- Good for intermittent bursts
- Reduces cold starts during active periods

**Long (120s)**:
- Minimize cold starts
- Better user experience
- Higher costs

**Recommendation**: Start with 10-30s, adjust based on traffic patterns.

#### Execution Timeout

Maximum time a single job can run.

**Formula**: `Typical Workflow Duration × 1.2`

Examples:
- SD 1.5 (20 steps): ~10-15s → Set 30s
- SDXL (30 steps): ~30-40s → Set 60s
- FLUX (50 steps): ~90-120s → Set 180s

**Pro Tip**: Monitor execution times and set to 95th percentile + 20% buffer.

### 5. Scaling Strategy

#### Queue Delay (Recommended)

Scales up when requests wait longer than threshold.

**Settings**:
- Delay Threshold: 4-8 seconds typical
- Works well for variable traffic
- Responsive to demand spikes

**Best For**: Production endpoints with variable load.

#### Request Count

Scales based on formula: `(Queued + In Progress) / N`

**Settings**:
- Typically N=4 (default)
- More predictable scaling
- Can over-provision during bursts

**Best For**: Steady, predictable traffic.

### 6. FlashBoot

**Always Enable** - No downside, significantly reduces cold starts.

How it works:
- Keeps resources warm after use
- Faster subsequent worker spawns
- No additional cost

### 7. Model Caching (Beta)

Speeds up cold starts by placing workers on hosts with cached models.

**Setup**:
1. Go to Endpoint Configuration
2. Find "Model (optional)" field
3. Add model URLs:
   ```
   https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0
   https://huggingface.co/black-forest-labs/FLUX.1-dev
   ```
4. Add Hugging Face token if needed (for gated models)

**Benefits**:
- Workers start in seconds on cached hosts
- No download charges
- Fallback to download if no cached hosts

**Limitations**:
- Beta feature
- May limit data center availability
- Depends on RunPod's cache distribution

**When to Use**:
- Standard models from Hugging Face
- Minimize cold start times
- Willing to help test beta feature

**When to Skip**:
- Custom/proprietary models
- Using network volumes (already fast)
- Need maximum data center flexibility

### 8. Network Volume vs. Model Caching

**Network Volume**:
- ✅ Any models (custom, fine-tuned, LoRAs, etc.)
- ✅ Full control over model versions
- ✅ Shared across all workers
- ✅ Proven, stable feature
- ❌ Locked to one data center
- ❌ Monthly storage cost ($0.05-0.07/GB)

**Model Caching**:
- ✅ No storage cost
- ✅ All data centers available
- ✅ Faster cold starts
- ❌ Limited to Hugging Face models
- ❌ Beta stability
- ❌ Less control over versions

**Recommendation**:
- **Network Volume** for production with custom models
- **Model Caching** for standard models or testing
- **Both** can be used together!

## Cost Optimization Strategies

### Strategy 1: Scale to Zero

```
Active Workers: 0
Idle Timeout: 5s
FlashBoot: Enabled
```

**Cost**: Only pay for actual usage
**Trade-off**: Cold starts of 10-30s

**Best for**: Low traffic, dev/testing

### Strategy 2: Single Active Worker

```
Active Workers: 1
Idle Timeout: 30s
Max Workers: 5
```

**Cost**: ~$17/day baseline
**Trade-off**: First request instant, others may cold start

**Best for**: Moderate traffic, cost-conscious production

### Strategy 3: Full Coverage

```
Active Workers: (Peak Concurrency)
Idle Timeout: 60s
```

**Cost**: ~$17/day per worker
**Trade-off**: Highest cost, zero cold starts

**Best for**: High SLA requirements, steady traffic

### Hidden Cost Factors

1. **Container Disk**: Included in GPU pricing
2. **Network Volume**: $0.05-0.07/GB/month separate charge
3. **Bandwidth**: Included for images <10MB typically
4. **API Calls**: Free
5. **Failed Jobs**: Not charged if worker never started

## Monitoring & Optimization

### Key Metrics to Track

1. **Cold Start Frequency**
   - If >20% of requests: Increase active workers or idle timeout

2. **Average Execution Time**
   - If consistently near timeout: Increase execution timeout
   - If much faster than timeout: Reduce timeout to save on stuck jobs

3. **Queue Wait Time**
   - If regularly >5s: Increase max workers or scaling aggressiveness

4. **Worker Utilization**
   - If <50%: Reduce active workers
   - If >90%: Add more active workers

5. **Cost per Request**
   - Track: `Daily Cost / Total Requests`
   - Optimize by balancing active workers vs. cold starts

### Optimization Cycle

1. **Week 1**: Start conservative (0 active workers, moderate max)
2. **Week 2**: Analyze metrics, adjust based on traffic patterns
3. **Week 3**: Fine-tune timeouts and scaling thresholds
4. **Week 4**: Settle on optimal configuration

**Pro Tip**: Make one change at a time, wait 24-48 hours to measure impact.

## Common Configurations by Use Case

### Personal Project
```
Active: 0, Max: 2, Idle: 5s
Cost: $1-5/day
```

### Startup MVP
```
Active: 1, Max: 5, Idle: 20s
Cost: $20-30/day
```

### Growing SaaS
```
Active: 3, Max: 10, Idle: 30s
Cost: $50-80/day
```

### Enterprise Production
```
Active: 10+, Max: 50+, Idle: 60s
Cost: $200+/day
```

## Advanced Tips

1. **Multi-Region Setup**: Deploy identical endpoints in different regions for redundancy
2. **Webhook Notifications**: Configure webhooks for job completion (async UX)
3. **Priority Queues**: Use separate endpoints for premium vs. free tier users
4. **A/B Testing**: Run two endpoints with different configs, compare metrics
5. **Scheduled Scaling**: Use RunPod API to adjust active workers based on time of day

## Next Steps

1. Start with Template 2 (Moderate Traffic)
2. Monitor for 3-7 days
3. Adjust based on actual usage patterns
4. Review costs weekly
5. Optimize progressively

## Questions?

- Discord: RunPod community
- Docs: https://docs.runpod.io
- Support: support@runpod.io
