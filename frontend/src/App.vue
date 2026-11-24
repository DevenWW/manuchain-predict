<template>
  <main>
    <header>
      <p class="eyebrow">MANUCHAIN / EQUIPMENT ANALYTICS</p>
      <h1>Equipment Condition Prediction</h1>
      <p>Configure data inputs, run predictions, and review results.</p>
    </header>

    <nav class="navigation" aria-label="Pages">
      <button v-for="item in pages" :key="item.id" type="button" :class="{ selected: page === item.id }" :aria-current="page === item.id ? 'page' : null" :disabled="busy" @click="openPage(item.id)">{{ item.label }}</button>
    </nav>

    <div v-if="error" class="message error" role="alert">{{ error }}</div>
    <div v-else-if="notice" class="message" role="status">{{ notice }}</div>

    <section v-if="page === 'interface'" aria-labelledby="interface-title">
      <div class="heading"><div><p class="eyebrow">DATA INTERFACE</p><h2 id="interface-title">Interface Settings</h2></div><span class="badge" :class="{ active: status.online_enabled }">{{ status.online_enabled ? 'Online reception enabled' : 'Online reception stopped' }}</span></div>
      <p class="description">Map Java signal names to the model’s 15 input features. Signal names must contain 1–64 letters, digits, underscores or hyphens. Device fields and units remain unverified; the current mapping is for simulation.</p>
      <div class="note">Configure the OPC UA endpoint, nodes and connection parameters in the Java collector. Mappings saved here apply only to the current service session and reset on restart. Stop online reception before changing them.</div>
      <p class="mapping-heading">Signal name <span>→</span> Model feature</p>
      <div class="mapping-grid">
        <label v-for="(feature, index) in features" :key="feature" class="mapping-row">
          <span class="sr-only">{{ feature }} signal name</span>
          <input v-model.trim="signalNames[index]" type="text" :disabled="!mappingLoaded || status.online_enabled || busy" :placeholder="'Enter signal name'">
          <span class="arrow">→</span><code>{{ feature }}</code>
        </label>
      </div>
      <button class="primary" type="button" :disabled="busy || !mappingLoaded || status.online_enabled" @click="saveMapping">Save mapping</button>
    </section>

    <section v-else-if="page === 'predict'" aria-labelledby="predict-title">
      <div class="heading"><div><p class="eyebrow">PREDICTION SETUP</p><h2 id="predict-title">Prediction Settings</h2></div><span class="badge" :class="{ active: status.online_enabled }">{{ status.online_enabled ? 'Online reception enabled' : 'Online reception stopped' }}</span></div>
      <div class="mode-tabs" role="group" aria-label="Data mode">
        <button type="button" :class="{ selected: selectedMode === 'offline' }" :aria-pressed="selectedMode === 'offline'" @click="selectedMode = 'offline'">Offline CSV</button>
        <button type="button" :class="{ selected: selectedMode === 'online' }" :aria-pressed="selectedMode === 'online'" @click="selectedMode = 'online'">Online Java</button>
      </div>
      <div v-if="selectedMode === 'offline'" class="mode-body">
        <h3>CSV Batch Prediction</h3>
        <p>Select a local CSV file to run the trained model. Include record_id and sensor_01 through sensor_15; remaining life is not required for prediction.</p>
        <div class="file-label">CSV file</div>
        <input ref="csvFile" type="file" accept=".csv,text/csv" hidden @change="selectFile">
        <button class="file-button" type="button" @click="$refs.csvFile.click()">Choose file</button>
        <span class="file-name" aria-live="polite">{{ fileName || 'No file chosen' }}</span>
        <div><button class="primary" type="button" :disabled="busy || !file" @click="runOffline">{{ busy ? 'Processing…' : 'Run prediction' }}</button></div>
      </div>
      <div v-else class="mode-body">
        <h3>Java Device Data</h3>
        <p>Receive data from Java and run the same model. Check the mapping in Interface Settings first. Demonstration data does not represent a real device.</p>
        <p class="source-detail">Signal mapping: {{ sourceLabel }}</p>
        <div class="actions"><button class="primary" type="button" :disabled="busy || status.online_enabled" @click="setOnline(true)">Start reception</button><button class="secondary" type="button" :disabled="busy || !status.online_enabled" @click="setOnline(false)">Stop reception</button></div>
      </div>
      <div v-if="status.message" class="message" role="status">{{ status.message }}</div>
    </section>

    <section v-else aria-labelledby="result-title">
      <div class="heading"><div><p class="eyebrow">PREDICTIONS</p><h2 id="result-title">Prediction Results</h2></div><span class="source">{{ modeLabel }}</span></div>
      <p class="model">Model source: {{ status.model_source || 'Not loaded' }} · Prediction probabilities are for research and have not been validated in operation.</p>
      <div class="summary"><div><span>Records</span><strong>{{ predictions.length }}</strong></div><div><span>Predicted below 7 days</span><strong>{{ riskCount }}</strong></div><div><span>Online reception</span><strong class="small">{{ status.online_enabled ? 'Enabled' : 'Stopped' }}</strong></div></div>
      <label class="filter"><input type="checkbox" v-model="riskOnly"> Show only records predicted below 7 days</label>
      <div v-if="!predictions.length" class="empty">No predictions yet. Prepare a model, then run an offline prediction or start online reception.</div>
      <div v-else class="table-wrap"><table><thead><tr><th>Record ID</th><th>Probability of less than 7 days</th><th>Predicted class</th></tr></thead><tbody><tr v-for="(row, index) in visibleRows" :key="index"><td>{{ row.record_id }}</td><td>{{ formatProbability(row.risk_probability) }}</td><td>{{ row.predicted_at_risk ? 'Less than 7 days' : '7 days or more' }}</td></tr><tr v-if="!visibleRows.length"><td colspan="3">No records match the filter</td></tr></tbody></table></div>
    </section>
  </main>
</template>
<script>
const features = Array.from({length: 15}, (_, i) => `sensor_${String(i + 1).padStart(2, '0')}`)
const emptyStatus = () => ({mode: '', online_enabled: false, model_source: '', predictions: [], message: '', online_source: ''})
export default {
  data: () => ({status: emptyStatus(), page: 'interface', pages: [{id: 'interface', label: 'Interface Settings'}, {id: 'predict', label: 'Prediction Settings'}, {id: 'results', label: 'Prediction Results'}], features, signalNames: features.slice(), mappingLoaded: false, selectedMode: 'offline', file: null, fileName: '', busy: false, error: '', notice: '', riskOnly: false, timer: null, requestVersion: 0}),
  computed: {
    predictions() { return Array.isArray(this.status.predictions) ? this.status.predictions : [] },
    visibleRows() { return this.riskOnly ? this.predictions.filter(x => x.predicted_at_risk) : this.predictions },
    riskCount() { return this.predictions.filter(x => x.predicted_at_risk).length },
    modeLabel() { return this.status.mode === 'online' ? 'Online mode' : this.status.mode === 'offline' ? 'Offline mode' : 'Waiting for data' },
    sourceLabel() { return this.status.online_source === 'synthetic demonstration' ? 'Simulation default' : ['configured signals', 'user-configured signals'].includes(this.status.online_source) ? 'User configured (does not indicate a connected device)' : 'Unknown' }
  },
  async mounted() {
    await this.refreshStatus()
    await this.loadMapping()
    this.timer = window.setInterval(() => { if (!this.busy && this.status.online_enabled) this.refreshStatus() }, 3000)
  },
  beforeDestroy() { window.clearInterval(this.timer) },
  methods: {
    async request(url, options) {
      const response = await fetch(url, {...options, cache: 'no-store'})
      let data
      try { data = await response.json() } catch (_) { throw new Error(`The service returned unreadable data（${response.status}）`) }
      if (!response.ok) throw new Error(data.error || data.message || `Request failed（${response.status}）`)
      return data
    },
    updateStatus(data) { this.status = {...this.status, ...data, predictions: Array.isArray(data.predictions) ? data.predictions : this.predictions} },
    async refreshStatus() {
      const version = this.requestVersion
      try { const data = await this.request('/api/status'); if (version === this.requestVersion) { this.updateStatus(data); if (this.error.startsWith('Cannot connect to local service: ')) this.error = '' } }
      catch (err) { if (version === this.requestVersion) this.error = `Cannot connect to local service: ${err.message}` }
    },
    async loadMapping() {
      this.mappingLoaded = false
      try {
        const data = await this.request('/api/interface')
        const inverse = Object.fromEntries(Object.entries(data.mapping || {}).map(([signal, feature]) => [feature, signal]))
        this.signalNames = this.features.map(feature => inverse[feature] || '')
        this.updateStatus(data)
        this.mappingLoaded = true
      } catch (err) { this.error = `Cannot load interface settings: ${err.message}` }
    },
    async saveMapping() {
      const names = this.signalNames.map(name => name.trim())
      if (names.some(name => !/^[A-Za-z0-9_-]{1,64}$/.test(name)) || new Set(names).size !== this.features.length) { this.error = 'Enter a unique signal name for each feature using 1–64 letters, digits, underscores or hyphens.'; return }
      this.busy = true; this.error = ''; this.notice = ''; this.requestVersion++
      try {
        const mapping = Object.fromEntries(names.map((name, index) => [name, this.features[index]]))
        const data = await this.request('/api/interface', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({mapping})})
        this.updateStatus(data); await this.refreshStatus(); this.notice = 'Mapping saved for the current service session.'
      } catch (err) { this.error = err.message }
      finally { this.busy = false }
    },
    openPage(page) { if (this.busy || page === this.page) return; this.page = page; this.error = ''; this.notice = ''; if (page === 'interface') this.loadMapping(); else if (page === 'results') this.refreshStatus() },
    selectFile(event) { this.file = event.target.files[0] || null; this.fileName = this.file ? this.file.name : ''; this.error = '' },
    async runOffline() {
      if (!this.file) return
      this.busy = true; this.error = ''; this.notice = ''; this.requestVersion++
      try {
        const csv = await this.file.text()
        const data = await this.request('/api/offline', {method: 'POST', headers: {'Content-Type': 'text/csv; charset=utf-8'}, body: csv})
        this.updateStatus(data); this.page = 'results'
      } catch (err) { this.error = err.message }
      finally { this.busy = false }
    },
    async setOnline(start) {
      this.busy = true; this.error = ''; this.notice = ''; this.requestVersion++
      try { const data = await this.request(`/api/online/${start ? 'start' : 'stop'}`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}'}); this.updateStatus(data); await this.refreshStatus() }
      catch (err) { this.error = err.message }
      finally { this.busy = false }
    },
    formatProbability(value) { return typeof value === 'number' && Number.isFinite(value) ? `${(value * 100).toFixed(1)}%` : '—' }
  }
}
</script>
<style>
*{box-sizing:border-box}body{margin:0;background:#f2f5f7;color:#1d2e3e;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}main{max-width:1120px;margin:auto;padding:48px 28px}header{margin-bottom:28px}header>p:last-child{color:#526775}.eyebrow{font-size:11px;font-weight:700;letter-spacing:.15em;color:#167d77;margin:0 0 8px}h1{font-size:36px;margin:0 0 10px;letter-spacing:-.03em}h2{font-size:23px;margin:0}h3{font-size:18px;margin:0 0 8px}p{line-height:1.65}section{background:#fff;border:1px solid #e2e9ed;border-radius:14px;padding:28px;margin:20px 0;box-shadow:0 5px 20px rgba(25,55,65,.035)}.navigation{display:flex;gap:8px;flex-wrap:wrap}.navigation button{padding:10px 18px;border:1px solid #d4e2e4;border-radius:8px;background:#fff;color:#526775;cursor:pointer;font-size:14px}.navigation button.selected{background:#174e4c;color:#fff;border-color:#174e4c;font-weight:700}.heading{display:flex;justify-content:space-between;align-items:center;gap:12px}.badge,.source{font-size:12px;background:#edf1f3;color:#566972;padding:7px 12px;border-radius:20px;white-space:nowrap}.badge.active{background:#e1f5ed;color:#176f50}.description,.mode-body p{color:#526775}.note{background:#f3f7f7;color:#526775;padding:14px;border-radius:8px;font-size:13px;line-height:1.6}.mapping-heading{font-weight:600;font-size:14px;margin-top:24px}.mapping-heading span{color:#76908f;margin:0 4px}.mapping-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.mapping-row{display:flex;align-items:center;gap:8px;min-width:0}.mapping-row input{min-width:0;width:100%;padding:9px;border:1px solid #cfdbde;border-radius:6px;font:inherit}.mapping-row code{font-size:12px;color:#265752}.arrow{color:#90a5a5}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}.mode-tabs{display:flex;gap:8px;border-bottom:1px solid #e4eaed;margin-top:23px}.mode-tabs button{border:0;background:none;padding:12px 18px;border-bottom:3px solid transparent;color:#526775;font-size:15px;cursor:pointer}.mode-tabs button.selected{border-color:#147b74;color:#116961;font-weight:700}.mode-body{padding-top:24px;max-width:760px}.source-detail{font-size:13px}.file-label{display:block;font-weight:600;margin:20px 0 8px}.file-name{font-size:13px;margin-left:10px}.actions{display:flex;gap:10px}button.primary,button.secondary{padding:10px 18px;border-radius:7px;font-weight:600;cursor:pointer;margin-top:20px}.primary{background:#147b74;color:white;border:1px solid #147b74}.secondary{background:white;color:#335361;border:1px solid #c9d7dc}button:disabled{opacity:.45;cursor:not-allowed}.message{background:#edf7f5;color:#275e59;border-radius:8px;padding:12px 14px;margin-top:20px;line-height:1.5}.message.error{background:#fff2ef;color:#9c392a}.model{color:#667985;font-size:14px}.summary{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:24px 0}.summary div{display:flex;flex-direction:column;gap:10px;background:#f4f8f8;border:1px solid #e4eeee;border-radius:10px;padding:18px}.summary strong{font-size:30px;color:#124d4b}.summary strong.small{font-size:18px}.summary span,.filter{font-size:13px;color:#647883}.filter{display:block;margin:12px 0 18px}.empty{padding:30px;background:#f7f9fa;color:#647883;border-radius:8px}.table-wrap{max-height:420px;overflow:auto}table{width:100%;border-collapse:collapse;text-align:left}th,td{padding:13px;border-bottom:1px solid #e3eaed}th{font-size:13px;color:#617681;background:#f6f9f9;position:sticky;top:0}tbody tr:nth-child(even){background:#f8fafb}@media(max-width:800px){.mapping-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:600px){main{padding:28px 14px}section{padding:20px}h1{font-size:28px}.heading{align-items:flex-start;flex-direction:column}.mode-tabs button{padding:10px 12px}.mapping-grid{grid-template-columns:1fr}.summary{gap:8px}.summary div{padding:12px}.summary strong{font-size:24px}}
</style>
