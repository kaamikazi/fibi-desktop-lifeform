export type MemoryCategory =
  | "fact"
  | "event"
  | "project"
  | "habit"
  | "belief"
  | "goal"
  | "important_moment";

export type FibiMood =
  | "happy"
  | "sleepy"
  | "curious"
  | "focused"
  | "excited"
  | "annoyed"
  | "idle";

export type PresenceState =
  | "idle"
  | "thinking"
  | "speaking"
  | "listening"
  | "observing"
  | "napping"
  | "waking"
  | "being_dragged";

export interface Memory {
  id: number | null;
  category: MemoryCategory;
  content: string;
  importance: number;
  source: string;
  createdAt: string;
  updatedAt: string;
  lastAccessedAt: string;
  accessCount: number;
  confidence: number;
  emotionalWeight: number;
  metadata: Record<string, unknown>;
}

export interface Observation {
  timestamp: string;
  timeOfDay: "morning" | "afternoon" | "evening" | "night" | "late_night";
  activeApp: string | null;
  activeWindowTitle: string | null;
  clipboardText: string | null;
}

export interface PersonalityContext {
  systemPrompt: string;
  mood: FibiMood;
  observation: Observation;
  memories: Memory[];
  memoryHints: string[];
  patterns: DetectedPattern[];
}

export interface FibiResponse {
  displayText: string;
  ttsText: string;
  mood: FibiMood | string;
  modelUsed: string;
  usedFallback: boolean;
  timing: TimingResult | null;
  motion: MotionIntent | null;
}

export interface JournalEntry {
  id: number | null;
  timestamp: string;
  eventType: string;
  mood: string;
  presenceState: PresenceState;
  shortSummary: string;
  relatedProject: string | null;
  emotionalWeight: number;
  source: string;
  metadata: Record<string, unknown>;
}

export interface DetectedPattern {
  pattern: string;
  confidence: number;
  summary: string;
  suggestedReaction: string;
}

export interface BondState {
  affection: number;
  trust: number;
  comfort: number;
  mischief: number;
  attachmentLevel: number;
  lastAffectionEventAt: string | null;
}

export interface AttentionResult {
  attentionLevel: number;
  reason: string;
  shouldReact: boolean;
  reactionType: string;
}

export interface HabitState {
  name: string;
  line: string;
  lastPerformedAt: string;
  timesPerformed: number;
}

export interface InteractionEvent {
  eventType: string;
  timestamp: string;
  direct: boolean;
  metadata: Record<string, unknown>;
}

export interface NapState {
  isNapping: boolean;
  napStartedAt: string | null;
  lastWokeAt: string | null;
  energy: number;
}

export interface WindowPosition {
  x: number;
  y: number;
}

export interface CreatureReaction {
  text: string;
  expression: string;
  reactionType: string;
  shouldDisplay: boolean;
  soundName: string | null;
  motion: MotionIntent | null;
  timing: TimingResult | null;
}

export interface RitualState {
  name: string;
  lastTriggeredAt: string | null;
  timesTriggered: number;
}

export interface RitualResult {
  name: string;
  reaction: CreatureReaction | null;
  triggered: boolean;
}

export interface NestState {
  position: WindowPosition | null;
  name: string;
  confidence: number;
  createdAt: string | null;
  lastNestedAt: string | null;
  timesReturnedToNest: number;
}

export interface DailySummary {
  date: string;
  mainMood: string;
  notableProject: string | null;
  interactionCount: number;
  tinySummary: string;
  emotionalWeight: number;
  notableEvents: string[];
  projects: string[];
}

export interface ProjectAffinity {
  projectName: string;
  mentionCount: number;
  lastSeenAt: string | null;
  affectionWeight: number;
  frustrationWeight: number;
  successWeight: number;
}

export interface ReactionCandidate {
  text: string;
  mood: string;
  minAffection: number;
  maxAnnoyance: number;
  timeOfDay: string | null;
  cooldownKey: string | null;
  weight: number;
  requiresTeasingAllowed: boolean;
  blockedWhenQuiet: boolean;
  blockedWhenBoundaryActive: boolean;
  minFamiliarity: number;
  maxUserAnnoyance: number;
  socialTone: "neutral" | "soft" | "playful" | "teasing" | "comfort" | "apology" | "boundary_ack" | "celebration";
  canBeMotionOnly: boolean;
}

export interface TimePersonalityCurve {
  timeOfDay: string;
  energyBias: number;
  sleepinessBias: number;
  curiosityBias: number;
  preferredMood: string;
}

export interface MotionIntent {
  motionName: string;
  durationMs: number;
  intensity: number;
  expressionHint: string | null;
  cooldownKey: string;
  canInterrupt: boolean;
  reason: string;
}

export interface TimingResult {
  preDelayMs: number;
  typingStyle: "instant" | "soft" | "sleepy" | "excited" | "thinking";
  showThinkingBubble: boolean;
  thinkingLine: string;
}

export interface ExpressionState {
  persistentExpression: string;
  currentExpression: string;
  temporaryExpression: string | null;
  minimumDurationMs: number;
  temporaryUntilMs: number | null;
}

export interface BubbleDisplayOptions {
  typingStyle: string;
  autoHideMs: number;
  allowRepeat: boolean;
  keepWhileSpeaking: boolean;
}

export interface RepetitionState {
  spokenLines: string[];
  reactionCategories: string[];
  motionNames: string[];
  rituals: string[];
  idleReactions: string[];
  projectReferences: string[];
}

export type SoundEvent = "click" | "happy" | "annoyed" | "sleep" | "wake" | "drag" | "success";

export type ActionRiskLevel = "safe" | "confirm_required" | "blocked_for_now";

export interface ActionIntent {
  actionType: string;
  target: string;
  query: string;
  rawText: string;
  confidence: number;
  directUserInitiated: boolean;
}

export interface ActionSettings {
  allowDesktopActions: boolean;
  allowOpenApps: boolean;
  allowWebSearch: boolean;
  allowVolumeControl: boolean;
  allowScreenshot: boolean;
  allowShutdown: boolean;
  allowUnknownExecutables: boolean;
  allowTerminalCommands: boolean;
  allowFileModification: boolean;
  allowClipboardActions: boolean;
  allowAutonomousActions: boolean;
}

export interface ActionPermissionResult {
  allowed: boolean;
  blocked: boolean;
  requiresConfirmation: boolean;
  reason: string;
  confirmationPrompt: string;
  fibiReply: string;
}

export interface DesktopActionResult {
  ok: boolean;
  message: string;
  actionType: string;
  target: string;
  providerUsed: string;
  error: string | null;
}

export interface PendingAction {
  actionType: string;
  target: string;
  query: string;
  createdAt: string;
  expiresAt: string;
  requiredConfirmationPhrase: string;
  riskLevel: ActionRiskLevel | string;
}

export interface ActionJournalEntry {
  timestamp: string;
  actionType: string;
  target: string;
  riskLevel: ActionRiskLevel | string;
  allowed: boolean;
  blocked: boolean;
  requiredConfirmation: boolean;
  confirmed: boolean;
  resultSummary: string;
  userInitiated: boolean;
}

export interface AppIndexEntry {
  displayName: string;
  normalizedName: string;
  path: string;
  source: string;
  confidence: number;
  lastSeenAt: string;
}

export interface AppSearchResult {
  matches: AppIndexEntry[];
  query: string;
}

export interface VoiceInputSettings {
  allowVoiceInput: boolean;
  pushToTalkEnabled: boolean;
  wakeWordEnabled: boolean;
  voiceConfirmationForActions: boolean;
  requireConfirmationBelowConfidence: number;
  voiceLanguage: string;
  voiceProvider: string;
  showTranscriptBeforeAction: boolean;
  saveVoiceAudio: boolean;
  saveTranscriptsToJournal: boolean;
  microphoneDeviceId: string | null;
  pushToTalkHotkey: string | null;
}

export interface VoiceListenState {
  state: "idle" | "listening" | "transcribing" | "confirm_transcript" | "routed" | "error" | string;
  source: "mic_button" | "slash_command" | "hotkey" | "future_wake_word" | string;
  startedAt: string | null;
  error: string | null;
}

export interface VoiceTranscriptionResult {
  transcript: string;
  rawText: string;
  confidence: number;
  durationMs: number;
  error: string | null;
  userConfirmed: boolean;
  source: "mic_button" | "slash_command" | "hotkey" | "future_wake_word" | string;
  shouldRouteToCore: boolean;
}

export interface VoiceCommandResult {
  handled: boolean;
  shouldRouteToCore: boolean;
  transcript: string;
  confidence: number;
  responseText: string;
  error: string | null;
  needsUserConfirmation: boolean;
  source: string;
}

export interface VoicePermissionResult {
  allowed: boolean;
  reason: string;
  fibiReply: string;
}

export interface VoiceDeviceInfo {
  deviceId: string;
  name: string;
  isDefault: boolean;
}

export interface PushToTalkState {
  enabled: boolean;
  hotkey: string | null;
  listening: boolean;
  source: string;
}

export type ContextSource =
  | "pasted_text"
  | "manual_selected_text"
  | "dropped_file"
  | "manual_file_open"
  | "voice_transcript"
  | "action_result"
  | "future_screen_reading_disabled";

export interface ContextItem {
  contextId: string;
  source: ContextSource | string;
  title: string;
  contentPreview: string;
  contentText: string;
  mimeType: string;
  filePath: string | null;
  createdAt: string;
  expiresAt: string;
  tokenEstimate: number;
  userInitiated: boolean;
  canRemember: boolean;
  remembered: boolean;
  sensitivityHint: string;
  error: string | null;
}

export interface ContextSession {
  items: ContextItem[];
  activeContextId: string | null;
}

export interface ContextReadResult {
  ok: boolean;
  item: ContextItem | null;
  message: string;
  error: string | null;
}

export interface ContextPermissionResult {
  allowed: boolean;
  reason: string;
  fibiReply: string;
}

export interface FileDropResult {
  ok: boolean;
  item: ContextItem | null;
  message: string;
  error: string | null;
}

export interface SelectedTextResult {
  ok: boolean;
  item: ContextItem | null;
  message: string;
  error: string | null;
}

export interface ContextSummary {
  contextId: string;
  title: string;
  summary: string;
  tokenEstimate: number;
  sensitivityHint: string;
}

export interface ContextMemoryDecision {
  shouldRemember: boolean;
  summary: string;
  reason: string;
}

export interface ProjectFileEntry {
  relativePath: string;
  fileName: string;
  extension: string;
  sizeBytes: number;
  lastModified: string;
  safeToRead: boolean;
  ignoredReason: string;
  contentPreview: string;
  tokenEstimate: number;
}

export interface ProjectNote {
  text: string;
  createdAt: string;
}

export interface ProjectWorkspace {
  projectId: string;
  name: string;
  rootPath: string;
  createdAt: string;
  lastOpenedAt: string;
  lastScannedAt: string;
  trusted: boolean;
  fileCount: number;
  detectedStack: string[];
  summary: string;
  userAdded: boolean;
  notes: ProjectNote[];
}

export interface ProjectScanResult {
  ok: boolean;
  workspace: ProjectWorkspace | null;
  files: ProjectFileEntry[];
  ignoredCount: number;
  message: string;
  error: string | null;
}

export interface ProjectSummary {
  projectId: string;
  name: string;
  detectedStack: string[];
  importantFiles: string[];
  folders: string[];
  summary: string;
}

export interface ProjectQuestionResult {
  handled: boolean;
  responseText: string;
  needsModel: boolean;
  contextHint: string;
}

export interface ProjectPermissionResult {
  allowed: boolean;
  reason: string;
  fibiReply: string;
}

export interface ProjectWorkspaceSettings {
  allowProjectWorkspaces: boolean;
  allowHiddenFolders: boolean;
  allowVscodeFolder: boolean;
  readableFileLimitBytes: number;
  autoScanOnAdd: boolean;
}

export interface ProjectRecentFile {
  relativePath: string;
  openedAt: string;
  reason: string;
}

export interface ReplacementBlock {
  filePath: string;
  startLine: number;
  endLine: number;
  before: string;
  after: string;
  explanation: string;
}

export interface UnifiedDiffSuggestion {
  filePath: string;
  diffText: string;
  lineCount: number;
}

export interface EditRiskAssessment {
  riskLevel: "low" | "medium" | "high" | "blocked" | string;
  reason: string;
  blocked: boolean;
  warnings: string[];
}

export interface EditSafetyResult {
  allowed: boolean;
  risk: EditRiskAssessment;
  refusedReason: string;
  fibiReply: string;
}

export interface ProjectFileEditSuggestion {
  filePath: string;
  summary: string;
  suggestedDiff: UnifiedDiffSuggestion | null;
  replacementBlocks: ReplacementBlock[];
  explanation: string;
}

export interface ProjectEditPlan {
  projectId: string;
  targetFiles: string[];
  userRequest: string;
  summary: string;
  riskLevel: string;
  requiresUserReview: boolean;
  canApplyAutomatically: boolean;
  explanation: string;
  refusedReason: string;
}

export interface ProjectEditRequest {
  projectId: string;
  targetFiles: string[];
  userRequest: string;
  explicitFile: boolean;
  source: string;
}

export interface EditSuggestionResult {
  ok: boolean;
  projectId: string;
  targetFiles: string[];
  userRequest: string;
  summary: string;
  riskLevel: string;
  requiresUserReview: boolean;
  canApplyAutomatically: false;
  suggestedDiff: UnifiedDiffSuggestion | null;
  replacementBlocks: ReplacementBlock[];
  explanation: string;
  refusedReason: string;
  displayText: string;
}

export interface PatchFileChange {
  filePath: string;
  beforeHash: string;
  afterHash: string;
  diffText: string;
  replacement: ReplacementBlock | null;
  applied: boolean;
  error: string;
}

export interface PatchPlan {
  patchId: string;
  projectId: string;
  targetFiles: string[];
  diffText: string;
  fileChanges: PatchFileChange[];
  beforeHash: string;
  afterHash: string;
  riskLevel: "low" | "medium" | "high" | "blocked" | string;
  summary: string;
  createdAt: string;
  expiresAt: string;
  requiresConfirmation: boolean;
  backupPaths: string[];
  applied: boolean;
  rolledBack: boolean;
  error: string;
}

export interface PatchApplyRequest {
  patchId: string;
  confirmationPhrase: string;
  userInitiated: boolean;
}

export interface PatchApplyResult {
  ok: boolean;
  patchId: string;
  message: string;
  appliedFiles: string[];
  backupPaths: string[];
  riskLevel: string;
  error: string;
}

export interface PatchBackup {
  patchId: string;
  projectId: string;
  originalRelativePath: string;
  backupPath: string;
  beforeHash: string;
  createdAt: string;
}

export interface PatchRollbackResult {
  ok: boolean;
  patchId: string;
  message: string;
  restoredFiles: string[];
  error: string;
}

export interface PatchRiskResult {
  allowed: boolean;
  riskLevel: "low" | "medium" | "high" | "blocked" | string;
  reason: string;
  requiresConfirmation: boolean;
  blocked: boolean;
  warnings: string[];
  fibiReply: string;
}

export interface PendingPatch {
  patch: PatchPlan;
  requiredConfirmationPhrase: "apply patch confirm" | string;
  createdAt: string;
  expiresAt: string;
}

export interface PatchReviewSummary {
  patchId: string;
  projectId: string;
  targetFiles: string[];
  riskLevel: string;
  summary: string;
  confirmationPhrase: string;
  manualReviewNote: string;
}

export interface ProjectCheckCommand {
  commandKey: string;
  commandArgs: string[];
  cwd: string;
  timeoutSeconds: number;
  riskLevel: string;
  display: string;
}

export interface CheckCommandPreset {
  commandKey: string;
  display: string;
  commandArgs: string[];
  riskLevel: "low" | "medium" | "high" | "blocked" | string;
  source: string;
  description: string;
}

export interface ProjectCheckRequest {
  checkId: string;
  projectId: string;
  commandKey: string;
  commandArgs: string[];
  cwd: string;
  timeoutSeconds: number;
  allowed: boolean;
  requiresConfirmation: boolean;
  riskLevel: string;
}

export interface ProjectCheckSafetyResult {
  allowed: boolean;
  riskLevel: string;
  reason: string;
  requiresConfirmation: boolean;
  error: string;
}

export interface PendingProjectCheck {
  request: ProjectCheckRequest;
  requiredConfirmationPhrase: "run check confirm" | string;
  createdAt: string;
  expiresAt: string;
}

export interface ProjectCheckOutputSummary {
  status: "success" | "failure" | "timeout" | "error" | string;
  summary: string;
  errorCount: number;
  warningCount: number;
  hints: string[];
}

export interface ProjectCheckResult {
  checkId: string;
  projectId: string;
  commandKey: string;
  commandArgs: string[];
  cwd: string;
  timeoutSeconds: number;
  startedAt: string;
  endedAt: string;
  exitCode: number | null;
  stdoutPreview: string;
  stderrPreview: string;
  outputPath: string;
  summary: string;
  error: string;
  riskLevel: string;
  timedOut: boolean;
}

export interface ProjectCheckHistoryEntry {
  checkId: string;
  projectId: string;
  commandKey: string;
  commandDisplay: string;
  exitCode: number | null;
  durationMs: number;
  summary: string;
  outputDir: string;
  createdAt: string;
}

export interface ProjectCheckSettings {
  allowProjectChecks: boolean;
  requireCheckConfirmation: boolean;
  allowLowRiskChecksWithoutConfirmation: boolean;
  checkTimeoutSeconds: number;
  maxCheckOutputChars: number;
  saveFullCheckOutput: boolean;
  autoSuggestCheckAfterPatch: boolean;
  autoRunCheckAfterPatch: boolean;
}

export interface ErrorLocation {
  filePath: string;
  line: number | null;
  column: number | null;
  raw: string;
}

export interface RelatedFileCandidate {
  relativePath: string;
  absolutePath: string;
  safeToRead: boolean;
  score: number;
  reason: string;
  snippet: string;
  suspectedLine: number | null;
  refusedReason: string;
}

export interface FixConfidenceResult {
  confidence: number;
  reason: string;
}

export interface CheckFailureAnalysis {
  checkId: string;
  projectId: string;
  errorType: string;
  errorMessage: string;
  relatedFiles: ErrorLocation[];
  suspectedFile: string;
  suspectedLine: number | null;
  confidence: number;
  refusedReason: string;
}

export interface CheckFixSuggestion {
  checkId: string;
  projectId: string;
  errorType: string;
  errorMessage: string;
  relatedFiles: string[];
  suspectedFile: string;
  suspectedLine: number | null;
  confidence: number;
  fixSummary: string;
  riskLevel: string;
  suggestedPatchId: string;
  requiresUserReview: boolean;
  refusedReason: string;
}

export interface CheckFixPlan {
  checkId: string;
  projectId: string;
  errorType: string;
  errorMessage: string;
  relatedFiles: string[];
  suspectedFile: string;
  suspectedLine: number | null;
  confidence: number;
  fixSummary: string;
  riskLevel: string;
  suggestedPatchId: string;
  requiresUserReview: boolean;
  refusedReason: string;
}

export interface PendingFixSuggestion {
  checkId: string;
  projectId: string;
  errorType: string;
  errorMessage: string;
  relatedFiles: string[];
  suspectedFile: string;
  suspectedLine: number | null;
  confidence: number;
  fixSummary: string;
  riskLevel: string;
  suggestedPatchId: string;
  requiresUserReview: boolean;
  refusedReason: string;
  createdAt: string;
}

export interface WorkSessionStep {
  stepId: string;
  title: string;
  description: string;
  stepType:
    | "inspect_project"
    | "read_file"
    | "summarize_project"
    | "suggest_edit"
    | "create_patch"
    | "apply_patch"
    | "run_check"
    | "analyze_check_failure"
    | "suggest_fix"
    | "ask_user"
    | "manual_instruction"
    | "done"
    | string;
  status: "pending" | "active" | "completed" | "blocked" | "skipped" | string;
  requiresConfirmation: boolean;
  allowedToRunAutomatically: boolean;
  relatedFiles: string[];
  resultSummary: string;
  error: string;
}

export interface WorkSession {
  sessionId: string;
  projectId: string;
  userGoal: string;
  status: "active" | "paused" | "completed" | "cancelled" | string;
  createdAt: string;
  updatedAt: string;
  currentStepIndex: number;
  steps: WorkSessionStep[];
  completedSteps: string[];
  pendingActionType: string;
  pendingConfirmation: string;
  notes: string[];
  riskLevel: string;
  lastResultSummary: string;
}

export interface WorkSessionPlan {
  userGoal: string;
  steps: WorkSessionStep[];
  riskLevel: string;
  notes: string[];
}

export interface WorkSessionState {
  activeSessionId: string;
  sessions: WorkSession[];
}

export interface WorkSessionProgress {
  sessionId: string;
  status: string;
  currentStepIndex: number;
  totalSteps: number;
  completedSteps: string[];
  currentStep: WorkSessionStep | null;
  nextStep: WorkSessionStep | null;
  summary: string;
}

export interface WorkSessionAction {
  actionType: string;
  description: string;
  requiresConfirmation: boolean;
  confirmationPhrase: string;
  blocked: boolean;
  reason: string;
}

export interface WorkSessionDecision {
  allowed: boolean;
  action: WorkSessionAction | null;
  message: string;
  waitingForUser: boolean;
}

export interface WorkSessionSummary {
  sessionId: string;
  projectId: string;
  userGoal: string;
  status: string;
  completedCount: number;
  totalSteps: number;
  lastResultSummary: string;
}

export type InnerThoughtCategory =
  | "idle_thought"
  | "sleepy_thought"
  | "curious_thought"
  | "project_thought"
  | "memory_thought"
  | "nest_thought"
  | "dream_fragment"
  | "tiny_worry"
  | "tiny_pride"
  | "silly_thought";

export interface InnerThought {
  id: number | null;
  timestamp: string;
  category: InnerThoughtCategory;
  mood: string;
  text: string;
  relatedMemoryId: number | null;
  relatedProject: string | null;
  emotionalWeight: number;
  shouldSurfaceToUser: boolean;
  source: string;
}

export interface DreamFragment {
  id: number | null;
  timestamp: string;
  dreamText: string;
  mood: string;
  relatedProject: string | null;
  emotionalWeight: number;
  surfacedToUser: boolean;
}

export interface PreferenceState {
  preferenceKey: string;
  value: string;
  confidence: number;
  formedFrom: string;
  lastUpdatedAt: string;
}

export interface OpinionResult {
  text: string;
  mood: string;
  confidence: number;
  evidenceCount: number;
  supported: boolean;
  source: string;
}

export interface MoodDriftResult {
  previousMood: string;
  newMood: string;
  reason: string;
  driftStrength: number;
}

export interface EmotionalWeightUpdate {
  eventType: string;
  weight: number;
  reason: string;
  relatedProject: string | null;
}

export interface ThoughtBubbleCandidate {
  text: string;
  expression: string;
  emotionalWeight: number;
  category: InnerThoughtCategory;
  motion: MotionIntent | null;
  shouldDisplay: boolean;
}

export interface MemorySourceInfo {
  category: string;
  source: string;
  confidence: number;
  emotionalWeight: number;
  createdAt: string;
  updatedAt: string;
  lastAccessedAt: string;
}

export interface MemoryCareAction {
  action: string;
  target: string;
  category: string | null;
  confirm: boolean;
}

export interface NotebookEntry {
  entryId: number | string | null;
  section: string;
  title: string;
  body: string;
  sourceInfo: MemorySourceInfo | null;
}

export interface MemoryCareResult {
  ok: boolean;
  message: string;
  entries: NotebookEntry[];
  exportPath: string | null;
  changedCount: number;
}

export interface MemoryReviewItem {
  memoryId: number;
  source: string;
  category: string;
  text: string;
  summary: string;
  createdAt: string;
  updatedAt: string;
  confidence: number;
  approved: boolean;
  pinned: boolean;
  archived: boolean;
  sensitiveFlag: string;
  sourceEventId: string;
  provenance: Record<string, unknown>;
  tags: string[];
  userVisible: boolean;
  deletionStatus: string;
}

export interface MemorySearchResult {
  item: MemoryReviewItem;
  score: number;
  similarity: number;
  rank: number;
}

export interface MemoryConsentState {
  memoryLearningEnabled: boolean;
  rememberProjectEvents: boolean;
  rememberBrowserNotes: boolean;
  rememberWorkflowSummaries: boolean;
  rememberUserPreferences: boolean;
  rememberPersonalityNotes: boolean;
  requireApprovalForSensitiveMemory: boolean;
  autoArchiveLowConfidenceMemory: boolean;
}

export interface MemoryEditRequest {
  memoryId: number;
  newText: string;
  userConfirmed: boolean;
  reason: string;
}

export interface MemoryDeleteRequest {
  memoryId: number | null;
  category: string;
  userConfirmed: boolean;
  reason: string;
  broadDelete: boolean;
}

export interface MemoryExportRequest {
  memoryIds: number[];
  includeArchived: boolean;
  includeSensitive: boolean;
  format: "json" | "markdown" | "both" | string;
}

export interface MemoryApprovalResult {
  ok: boolean;
  memoryId: number | null;
  message: string;
  requiresConfirmation: boolean;
}

export interface MemoryLearningStatus {
  enabled: boolean;
  consent: MemoryConsentState;
  summary: string;
}

export interface MemoryRiskResult {
  allowed: boolean;
  blocked: boolean;
  requiresApproval: boolean;
  sensitiveFlag: string;
  reason: string;
  safeSummary: string;
  maskedPreview: string;
}

export interface PrivacySettings {
  allowForegroundAppObservation: boolean;
  allowWindowTitleObservation: boolean;
  allowClipboardObservation: boolean;
  allowJournal: boolean;
  allowDreams: boolean;
  allowInnerThoughts: boolean;
  allowPatternDetection: boolean;
  allowIdleBubbles: boolean;
  allowTts: boolean;
  allowSounds: boolean;
  allowOllama: boolean;
  allowMemoryLearning: boolean;
  allowNvidiaApi: boolean;
  allowCloudModel: boolean;
  cloudContextLevel: "none" | "minimal" | "personality_only" | "memory_hint";
}

export interface ExportBundle {
  createdAt: string;
  version: string;
  memories: Record<string, unknown>[];
  journalSummaries: Record<string, unknown>[];
  dreams: Record<string, unknown>[];
  preferences: Record<string, unknown>[];
  projectAffinity: Record<string, unknown>[];
  lifeState: Record<string, unknown>;
  privacySettings: Record<string, unknown>;
}

export interface ResetRequest {
  scope: string;
  confirmation: string;
  createBackup: boolean;
}

export interface LocalCommandResult {
  handled: boolean;
  response: FibiResponse | null;
  referencedMemoryId: number | null;
}

export interface ModelRouterResult {
  providerUsed: "local" | "nvidia" | "ollama" | "fallback";
  modelUsed: string;
  durationMs: number;
  wasCloud: boolean;
  fallbackUsed: boolean;
  error: string | null;
  replyText: string;
}

export interface FastResponseCategory {
  category:
    | "greeting"
    | "tiny_status"
    | "affection_click_like"
    | "goodbye"
    | "thanks"
    | "success"
    | "frustration"
    | "privacy_command"
    | "memory_command"
    | "model_command"
    | "simple_chat"
    | "complex_chat"
    | "unknown";
  confidence: number;
  shouldUseModel: boolean;
}

export interface ResponseBudget {
  category: string;
  budgetMs: number;
  elapsedMs: number;
  budgetExceeded: boolean;
  fallbackUsed: boolean;
}

export interface ProviderHealth {
  available: boolean;
  lastLatencyMs: number;
  consecutiveFailures: number;
  disabledUntil: string | null;
}

export interface ModelHealthState {
  ollamaAvailable: boolean;
  cloudAvailable: boolean;
  lastOllamaLatencyMs: number;
  lastCloudLatencyMs: number;
  consecutiveModelFailures: number;
  providerDisabledUntil: string | null;
  lastSuccessfulProvider: string;
  averageReplyLatencyMs: number;
}

export interface PerformanceMetric {
  lastReplyTimeMs: number;
  providerUsed: string;
  fastPathUsed: boolean;
  modelLatencyMs: number;
  ttsLatencyMs: number;
  dbLatencyMs: number;
  averageReplyTimeMs: number;
  slowestRecentStep: string;
}

export interface LocalMicroBrainResult {
  text: string | null;
  mood: string;
  category: string;
  providerUsed: string;
  fallbackUsed: boolean;
  confidence: "high" | "medium" | "low" | string;
  handled: boolean;
}

export interface CloudProviderConfig {
  name: string;
  apiKey: string;
  baseUrl: string;
  model: string;
  timeoutSeconds: number;
  maxTokens: number;
  supportsStreaming: boolean;
  privacyLevel: string;
}

export interface CancelRequest {
  requested: boolean;
  reason: string;
  requestedAt: string | null;
}

export interface StreamingChunk {
  text: string;
  done: boolean;
  provider: string;
  sequence: number;
}

export interface AppSettings {
  startMinimized: boolean;
  minimizeToTray: boolean;
  alwaysOnTop: boolean;
  clickThroughMode: boolean;
  animationIntensity: "off" | "low" | "normal";
  bubbleTypingEffect: boolean;
  performanceDebugLogs: boolean;
  setupComplete: boolean;
  firstRunSkipped: boolean;
  allowProjectChecks: boolean;
  requireCheckConfirmation: boolean;
  allowLowRiskChecksWithoutConfirmation: boolean;
  checkTimeoutSeconds: number;
  maxCheckOutputChars: number;
  saveFullCheckOutput: boolean;
  autoSuggestCheckAfterPatch: boolean;
  autoRunCheckAfterPatch: boolean;
}

export interface TrayAction {
  action: string;
  label: string;
}

export interface SettingsUpdate {
  key: string;
  value: unknown;
}

export interface FirstRunState {
  completed: boolean;
  skipped: boolean;
  completedAt: string | null;
}

export interface AutostartState {
  enabled: boolean;
  method: string;
  targetPath: string;
  error: string | null;
}

export interface DataHealthResult {
  ok: boolean;
  message: string;
  checks: Record<string, boolean>;
}

export interface AssetHealthResult {
  ok: boolean;
  message: string;
  checks: Record<string, boolean>;
}

export interface ShutdownState {
  cleanShutdown: boolean;
  lastShutdownAt: string | null;
  uncleanShutdownDetected: boolean;
}

export interface GuiCommandResult {
  handled: boolean;
  action: string;
  message: string;
}

export interface RelationshipState {
  familiarityLevel: number;
  teasingAllowed: boolean;
  comfortWithSilence: number;
  userPrefersQuiet: boolean;
  userPrefersPlayful: boolean;
  userAnnoyanceLevel: number;
  lastBoundarySignalAt: string | null;
  lastApologyAt: string | null;
  socialWarmth: number;
  socialDistance: number;
  interactionStyle:
    | "shy"
    | "sleepy_friend"
    | "playful_roommate"
    | "quiet_companion"
    | "chaotic_gremlin"
    | "focused_guardian";
}

export interface BoundarySignal {
  level: "soft" | "hard";
  phrase: string;
  quietMinutes: number;
  shouldApologize: boolean;
}

export interface BoundaryState {
  active: boolean;
  level: string;
  startedAt: string | null;
  expiresAt: string | null;
  lastPhrase: string;
}

export interface QuietModeState {
  active: boolean;
  startedAt: string | null;
  expiresAt: string | null;
  reason: string;
  muteTts: boolean;
}

export interface SocialContextDecision {
  action: "allow" | "soften" | "replace" | "silence";
  text: string;
  reason: string;
  motionOnly: boolean;
}

export interface SocialPreferenceUpdate {
  key: string;
  value: unknown;
  confidence: number;
  reason: string;
}

export interface RelationshipCommandResult {
  ok: boolean;
  message: string;
  state: RelationshipState | null;
}

export interface BrowserSession {
  browserSessionId: string;
  taskGoal: string;
  createdAt: string;
  updatedAt: string;
  source: string;
  safetyLevel: string;
  requiresConfirmation: boolean;
  notes: string[];
  linkedProjectId: string;
  linkedIssueId: string;
  status: string;
}

export interface BrowserPageNote {
  browserSessionId: string;
  url: string;
  title: string;
  userProvidedText: string;
  summary: string;
  createdAt: string;
  updatedAt: string;
  source: string;
  safetyLevel: string;
  requiresConfirmation: boolean;
  notes: string[];
  linkedProjectId: string;
  linkedIssueId: string;
  noteId: string;
}

export interface BrowserTaskPlan {
  browserSessionId: string;
  taskGoal: string;
  steps: string[];
  createdAt: string;
  updatedAt: string;
  source: string;
  safetyLevel: string;
  requiresConfirmation: boolean;
  notes: string[];
  linkedProjectId: string;
  linkedIssueId: string;
}

export interface BrowserOpenRequest {
  browserSessionId: string;
  url: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  source: string;
  safetyLevel: string;
  requiresConfirmation: boolean;
  notes: string[];
  linkedProjectId: string;
  linkedIssueId: string;
  domain: string;
}

export interface BrowserSafetyResult {
  allowed: boolean;
  blocked: boolean;
  safetyLevel: string;
  requiresConfirmation: boolean;
  reason: string;
  fibiReply: string;
  normalizedUrl: string;
  domain: string;
}

export interface BrowserSummaryResult {
  ok: boolean;
  summary: string;
  title: string;
  source: string;
  safetyLevel: string;
  requiresConfirmation: boolean;
  notes: string[];
  linkedProjectId: string;
  linkedIssueId: string;
}

export interface BrowserResearchNote {
  browserSessionId: string;
  url: string;
  title: string;
  userProvidedText: string;
  summary: string;
  taskGoal: string;
  createdAt: string;
  updatedAt: string;
  source: string;
  safetyLevel: string;
  requiresConfirmation: boolean;
  notes: string[];
  linkedProjectId: string;
  linkedIssueId: string;
}

export interface PendingBrowserAction {
  browserSessionId: string;
  actionType: string;
  url: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  source: string;
  safetyLevel: string;
  requiresConfirmation: boolean;
  notes: string[];
  linkedProjectId: string;
  linkedIssueId: string;
  domain: string;
}

export type WorkflowRecipeCategory =
  | "project_debug"
  | "project_release"
  | "beta_qa"
  | "browser_research"
  | "business_outreach"
  | "issue_report"
  | "daily_startup"
  | "custom";

export type WorkflowRecipeStepType =
  | "ask_user"
  | "inspect_project"
  | "read_safe_file"
  | "suggest_patch"
  | "apply_patch_confirmed"
  | "run_check_confirmed"
  | "analyze_check"
  | "browser_open_confirmed"
  | "summarize_pasted_page"
  | "create_issue"
  | "export_support_bundle"
  | "build_release_confirmed"
  | "manual_step"
  | "done"
  | string;

export interface WorkflowRecipeStep {
  stepId: string;
  title: string;
  instruction: string;
  stepType: WorkflowRecipeStepType;
  requiresConfirmation: boolean;
  allowedToAutoRun: boolean;
  linkedCommand: string;
  expectedInput: string;
  safetyNotes: string;
  status: string;
}

export interface WorkflowRecipe {
  recipeId: string;
  name: string;
  description: string;
  category: WorkflowRecipeCategory | string;
  version: string;
  steps: WorkflowRecipeStep[];
  safetyLevel: string;
  createdAt: string;
  updatedAt: string;
  builtIn: boolean;
  enabled: boolean;
}

export interface WorkflowRun {
  runId: string;
  recipeId: string;
  recipeName: string;
  status: "active" | "paused" | "completed" | "cancelled" | string;
  createdAt: string;
  updatedAt: string;
  currentStepIndex: number;
  steps: WorkflowRecipeStep[];
  completedSteps: string[];
  skippedSteps: string[];
  linkedSessionId: string;
  linkedProjectId: string;
  linkedIssueIds: string[];
  linkedSupportBundles: string[];
  linkedReleaseArtifacts: string[];
  safeSummaries: string[];
  safetyLevel: string;
}

export interface WorkflowRunState {
  activeRunId: string;
  runs: WorkflowRun[];
}

export interface WorkflowStepResult {
  ok: boolean;
  message: string;
  stepId: string;
  stepType: string;
  completed: boolean;
  waitingForUser: boolean;
  blocked: boolean;
}

export interface WorkflowRecipeSafetyResult {
  allowed: boolean;
  blocked: boolean;
  safetyLevel: string;
  reason: string;
  warnings: string[];
}

export interface WorkflowRunSummary {
  runId: string;
  recipeName: string;
  status: string;
  startedAt: string;
  completedAt: string;
  stepsCompleted: number;
  totalSteps: number;
  skippedSteps: string[];
  linkedIssues: string[];
  linkedSupportBundles: string[];
  linkedReleaseArtifacts: string[];
  safeSummaries: string[];
}

export interface WorkflowExport {
  runId: string;
  markdownPath: string;
  jsonPath: string;
  createdAt: string;
  excluded: string[];
}
