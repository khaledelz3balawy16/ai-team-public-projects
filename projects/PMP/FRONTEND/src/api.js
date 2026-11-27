const BASE = import.meta.env.VITE_API_BASE_URL || '/api/pmp'
const API_TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT_MS || 30000)
const AI_REPORT_TIMEOUT_MS = Number(import.meta.env.VITE_AI_REPORT_TIMEOUT_MS || 130000)

function getCookie(name) {
  return document.cookie.split('; ').find(row=>row.startsWith(`${name}=`))?.split('=').slice(1).join('=') || ''
}

async function fetchWithTimeout(url, options={}, timeoutMs=API_TIMEOUT_MS) {
  const controller = new AbortController()
  const timeout = window.setTimeout(()=>controller.abort(), timeoutMs)
  try { return await fetch(url, {...options, signal: controller.signal}) }
  catch(error) {
    if (error?.name === 'AbortError') throw new Error('The backend took too long to respond. Check that the Django server is running, then try again.')
    throw error
  }
  finally { window.clearTimeout(timeout) }
}

function sleep(ms) {
  return new Promise(resolve=>window.setTimeout(resolve, ms))
}

async function ensureCsrf() {
  const existing = getCookie('csrftoken')
  if (existing) return decodeURIComponent(existing)
  const response = await fetchWithTimeout(`${BASE}/csrf/`, {credentials:'include'})
  const data = await response.json().catch(()=>({}))
  return getCookie('csrftoken') || data.csrfToken || ''
}
async function request(path, options={}) {
  const {timeoutMs, ...fetchOptions} = options
  const method = (fetchOptions.method || 'GET').toUpperCase()
  const headers = {'Content-Type':'application/json', ...(fetchOptions.headers||{})}
  if (!['GET','HEAD','OPTIONS'].includes(method)) headers['X-CSRFToken'] = await ensureCsrf()
  let response
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try { response = await fetchWithTimeout(`${BASE}${path}`, {...fetchOptions, headers, credentials:'include'}, timeoutMs || API_TIMEOUT_MS) }
    catch(error) {
      if (error?.message?.includes('took too long')) throw error
      throw new Error('Cannot connect to the backend server. Check that it is running, then try again.')
    }
    const canRetry = ['GET','HEAD'].includes(method) && [502,503,504].includes(response.status) && attempt === 0
    if (!canRetry) break
    await sleep(700)
  }
  const contentType=response.headers.get('content-type')||''
  const data=contentType.includes('application/json')?await response.json().catch(()=>null):null
  if (!response.ok) {
    const detail=[502,503,504].includes(response.status) ? 'The backend is starting or temporarily unavailable. Please try again in a moment.' : data?.detail||data&&Object.values(data).flat().join(' ')
    const error = new Error(detail||`The server returned ${response.status} ${response.statusText}. Please try again.`)
    error.status = response.status
    error.data = data
    throw error
  }
  return data
}
export const api = {
  csrf:()=>ensureCsrf(),
  register:data=>request('/auth/register/',{method:'POST',body:JSON.stringify(data)}),
  login:data=>request('/auth/login/',{method:'POST',body:JSON.stringify(data)}),
  logout:()=>request('/auth/logout/',{method:'POST'}),
  verifyEmail:token=>request('/auth/verify-email/',{method:'POST',body:JSON.stringify({token})}),
  passwordReset:email=>request('/auth/password-reset/',{method:'POST',body:JSON.stringify({email})}),
  passwordResetConfirm:data=>request('/auth/password-reset/confirm/',{method:'POST',body:JSON.stringify(data)}),
  me:()=>request('/me/'), updateMe:data=>request('/me/',{method:'PATCH',body:JSON.stringify(data)}), dashboard:()=>request('/dashboard/',{timeoutMs:60000}),
  domains:()=>request('/domains/'), topics:domain=>request(`/topics/${domain?`?domain_id=${domain}`:''}`),
  createAttempt:data=>request('/attempts/',{method:'POST',body:JSON.stringify(data),timeoutMs:60000}), attempts:()=>request('/attempts/',{timeoutMs:60000}), attempt:id=>request(`/attempts/${id}/`), deleteAttempt:id=>request(`/attempts/${id}/`,{method:'DELETE'}),
  questions:id=>request(`/attempts/${id}/questions/`,{timeoutMs:60000}), reviewAnswer:(id,qid)=>request(`/attempts/${id}/questions/${qid}/review/`), saveAnswer:(id,qid,data)=>request(`/attempts/${id}/answers/${qid}/`,{method:'PUT',body:JSON.stringify(data)}),
  submit:id=>request(`/attempts/${id}/submit/`,{method:'POST',body:JSON.stringify({})}), abandon:id=>request(`/attempts/${id}/abandon/`,{method:'POST',body:JSON.stringify({})}),   result:id=>request(`/attempts/${id}/result/`),   report:id=>request(`/attempts/${id}/report/`),   generateReport:(id,data={})=>request(`/attempts/${id}/generate-report/`,{method:'POST',body:JSON.stringify(data),timeoutMs:AI_REPORT_TIMEOUT_MS}),   reportPdfUrl:id=>`${BASE}/attempts/${id}/report/pdf/`,
  adminQuestions:query=>request(`/admin/questions/${query?`?${query}`:''}`), questionBankStats:()=>request('/admin/questions/stats/'), updateAdminQuestion:(id,data)=>request(`/admin/questions/${id}/`,{method:'PATCH',body:JSON.stringify(data)}), importQuestions:data=>request('/admin/questions/import/',{method:'POST',body:JSON.stringify(data)}),
  adminProfiles:query=>request(`/admin/profiles/${query?`?${query}`:''}`), salesLeads:()=>request('/admin/profiles/sales-leads/'), kbcRegistry:()=>request('/admin/kbc-registry/')
}
