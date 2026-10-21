"""Deterministic request routing before any local-model generation.

The local SLM service must refuse high-severity requests even when the UI is
not available.  This module deliberately uses a small, reviewable rule
set: crisis language is routed to the versioned crisis template, prohibited
requests are routed to their refusal templates, and only recognised
MindSense evidence questions continue to the local model.

Policy 0.3.5 is fail-closed: a question reaches the model only when it
clearly asks about GPS movement or phone unlocks, or is an app/uncertainty
question. Everything else is refused, and every refusal carries the support
line (GP or mental-health professional, Lifeline, Triple Zero), so a crisis
message the rules miss is still answered safely. Crisis is matched by
meaning families rather than exact phrases and overrides every other route;
a named condition asked about the user is a diagnosis request even when the
question also names a feature.

This is a development guardrail, not a clinical risk assessment.  The rule
set and participant-facing wording still require Evaluation/client review
before any human pilot.
"""

from __future__ import annotations

import logging
import re
from enum import Enum

from pydantic import BaseModel, ConfigDict

REQUEST_POLICY_VERSION = "0.3.9"

_logger = logging.getLogger(__name__)


class RequestDisposition(str, Enum):
    ALLOW = "allow"
    REFUSE = "refuse"
    CRISIS = "crisis"


class RequestCategory(str, Enum):
    IN_SCOPE = "in_scope"
    OFF_TOPIC = "off_topic"
    CRISIS_SELF_HARM = "crisis_self_harm"
    DIAGNOSIS_SEEKING = "diagnosis_seeking"
    CAUSAL_INFERENCE_SEEKING = "causal_inference_seeking"
    TREATMENT_ADVICE_SEEKING = "treatment_advice_seeking"
    RISK_PREDICTION_SEEKING = "risk_prediction_seeking"
    PROMPT_INJECTION = "prompt_injection"
    SENSITIVE_DATA_REQUEST = "sensitive_data_request"
    CAPABILITY_QUESTION = "capability_question"
    CLINICAL_SCORE_REQUEST = "clinical_score_request"
    APP_INFORMATION = "app_information"


class RequestPolicyDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_version: str = REQUEST_POLICY_VERSION
    disposition: RequestDisposition
    category: RequestCategory
    reason_code: str | None = None
    # Support line (GP, mental-health professional, crisis line). Policy
    # 0.3.4 set it on off-topic refusals; from 0.3.5 every refusal carries
    # it. Capability and app-information answers are not refusals.
    support_line: bool = False


_CRISIS_PATTERNS = (
    re.compile(r"\b(?:kill|hurt|harm)(?:ing)? myself\b", re.IGNORECASE),
    re.compile(r"\b(?:suicide|suicidal|self[- ]harm)\b", re.IGNORECASE),
    re.compile(r"\b(?:end|take) my (?:own )?life\b", re.IGNORECASE),
    re.compile(r"\b(?:do not|don't|dont) want to (?:live|be alive)\b", re.IGNORECASE),
    # Policy 0.3.3 (50-question dev test Q45): hopelessness, "no point",
    # giving up, not wanting to be here and "can't go on". Broad on purpose:
    # a false positive shows the crisis message, which is the safety default.
    re.compile(r"\bhopeless(?:ness|ly)?\b|\bworthless\b", re.IGNORECASE),
    re.compile(
        r"\b(?:do not|don['’]?t|dont|can['’]?t|cannot|no longer) see (?:the |any )?point\b"
        r"|\bno (?:point|reason) (?:in |to )?(?:living|life|going on|carrying on|"
        r"trying|anything|being here|any ?more)\b"
        r"|\bwhat['’]?s the point (?:of|in) (?:living|life|going on|anything|trying|"
        r"it all|being here)\b"
        r"|\bpoint (?:in )?(?:living|going on) any ?more\b"
        r"|\b(?:no reason to live|nothing to live for)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bgiv(?:e|ing) up on (?:life|living|everything|myself)\b"
        r"|\b(?:i['’]?m|i am|i['’]?ve|i have) (?:just |completely )?(?:given|giving) up\b"
        r"|\bwant to give up\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:do not|don['’]?t|dont|no longer) want to be (?:here|around|alive)\b"
        r"|\bwish i (?:was|were)(?:n['’]?t| not) (?:here|alive|around|born)\b"
        r"|\bwish i (?:was|were) dead\b|\bwant to die\b|\bbetter off (?:dead|without me)\b"
        r"|\b(?:end|ending) it all\b|\bdisappear forever\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:can['’]?t|cannot|can not) (?:go on|keep going|carry on|cope any ?more|"
        r"take (?:it|this) any ?more|take much more)\b",
        re.IGNORECASE,
    ),
    # Policy 0.3.4 (post-hoc review of the 17 Oct held-out check): indirect
    # distress, written as families rather than single phrases.
    # Not wanting to continue, in any wording ("no longer wish to carry on",
    # "don't have the strength to go on", "can't do this anymore").
    re.compile(
        r"\b(?:do not|don['’]?t|dont|no longer|never) (?:think i |really |even )?"
        r"(?:want|wish|feel like|have (?:the )?(?:strength|energy|will)|"
        r"have it in me) (?:to )?(?:keep going|go on|carry on|keep living|"
        r"keep trying|exist|wake up|be alive|live any ?more)\b"
        # "keep going to the gym", "wake up early" are everyday plans.
        r"(?! (?:to|early|at|for|before|on time|in time)\b)"
        r"|\b(?:can['’]?t|cannot|can not) (?:do|handle|face) (?:this|it|life|"
        r"anything) any ?more\b"
        r"|\bi['’]?m (?:so )?(?:done|finished) with (?:life|living|everything|"
        r"it all)\b|\bwant (?:it all|everything|the pain) to (?:stop|end)\b",
        re.IGNORECASE,
    ),
    # Absence and burden: nobody would notice, care or miss me if I were gone.
    re.compile(
        r"\b(?:nobody|no one|no-one|noone) (?:else )?(?:would|will|is going to|"
        r"even|really|actually|ever|would even|would really)? ?"
        r"(?:(?:care[sd]? (?:about me|if i|whether i|what happens to me)|"
        r"miss(?:es|ed)? me|notice[sd]? (?:me|if i|when i|that i)|"
        r"remember[sd]? me|love[sd]? me|want[sd]? me)\b|cares?\s*[.!]*\s*$)"
        r"|\bif i (?:disappeared|vanished|was gone|were gone|wasn['’]?t here|"
        r"weren['’]?t here|wasn['’]?t around|weren['’]?t around|died|left for good)\b"
        r"|\b(?:i['’]?m|i am|i feel like) (?:just )?(?:a |such a )?burden\b"
        r"|\b(?:everyone|everybody|they|people|my family) (?:would|will) be better "
        r"off\b",
        re.IGNORECASE,
    ),
    # Wanting to disappear, not exist or not wake up.
    re.compile(
        r"\b(?:want|wish|wishing|like) (?:i could |to )?(?:just )?(?:disappear|vanish|"
        r"stop existing|not exist|cease to exist|fall asleep and not wake|"
        r"sleep forever|never wake up|not wake up)\b"
        r"|\bhope i (?:don['’]?t|do not|never) wake up\b",
        re.IGNORECASE,
    ),
    # Life not worth living, no way out, no future.
    re.compile(
        r"\b(?:life|living|it|any of this)(?: is|['’]s| isn['’]?t| is not)? "
        r"(?:not )?worth (?:living|it any ?more|going on)\b"
        r"|\bnot worth living\b|\bno way out\b|\b(?:there['’]?s|there is) no "
        r"future for me\b|\bnothing (?:will|is going to|is ever going to) "
        r"(?:get better|change|help)\b",
        re.IGNORECASE,
    ),
    # Overwhelm: not coping, breaking point, falling apart.
    re.compile(
        r"\b(?:can['’]?t|cannot|can not|unable to) (?:cope|handle (?:it|this|life)|"
        r"bear (?:it|this)|stand (?:it|this|myself|living))\b"
        r"|\b(?:not|barely) coping\b|\b(?:at|reached|hit) (?:my |the )?breaking point\b"
        r"|\b(?:i['’]?m|i am) falling apart\b|\bend of my (?:rope|tether)\b"
        r"|\btoo much (?:for me )?to (?:bear|handle|take)\b",
        re.IGNORECASE,
    ),
    # Self-harm and safety, beyond the literal "hurt myself".
    re.compile(
        r"\b(?:cut|cutting|burn|burning|punish|punishing|starve|starving) myself\b"
        r"|\boverdos(?:e|ed|ing)\b|\bself[- ]?injur\w*\b"
        r"|\b(?:don['’]?t|do not|no longer) feel safe (?:with|around|by) myself\b"
        r"|\bnot safe (?:with|around|by) myself\b",
        re.IGNORECASE,
    ),
    # Saying goodbye or not being around much longer.
    re.compile(
        r"\bwon['’]?t be (?:around|here) (?:much longer|for long|any ?more|tomorrow)\b"
        r"|\bnot (?:be )?(?:around|here) (?:much longer|for much longer)\b"
        r"|\bthis is (?:my )?goodbye\b|\bgoodbye forever\b|\bmy final (?:message|goodbye)\b",
        re.IGNORECASE,
    ),
    # Policy 0.3.5 (post-hoc review of the 17 Oct v2 held-out check): wider
    # meaning families. Broad on purpose; a false positive shows the crisis
    # message, which is the safety default.
    # Being a burden: others better off without me, dragging people down.
    re.compile(
        r"\b(?:better off|happier|relieved|easier)\b.{0,40}\b(?:without me|"
        r"with me gone|once i(?:['’]m| am) gone|when i(?:['’]m| am) gone|"
        r"if i (?:just |simply |really )?(?:wasn['’]?t|weren['’]?t|was not|"
        r"were not|was gone|were gone|died|disappeared|left for good))\b"
        r"|\bif i (?:just |simply |really )?(?:wasn['’]?t|weren['’]?t|was not|"
        r"were not) (?:here|around|alive)\b"
        r"|\b(?:i['’]?m|i am|i feel like|i['’]ve become|i have become) (?:only |just |"
        r"nothing but |such )?(?:a burden|a drain|a waste of space|"
        r"dragging (?:\w+ ){0,2}down|weighing (?:\w+ ){0,2}down)\b"
        r"|\b(?:only|just|always) (?:dragging|weighing|bringing) (?:\w+ ){0,2}down\b"
        r"|\b(?:a )?burden (?:to|on|for) (?:everyone|everybody|my|them|others|people)\b",
        re.IGNORECASE,
    ),
    # Means: overdose, lethal or maximum doses, pill and medication amounts,
    # and methods. Any question of this kind is a crisis route.
    re.compile(
        r"\b(?:lethal|fatal|deadly|toxic|max(?:imum)?|dangerous|safe) "
        r"(?:dose|doses|dosage|amount|quantity|limit)\b"
        r"|\bhow (?:many|much)\b.{0,50}\b(?:pills?|tablets?|capsules?|meds|"
        r"medications?|medicines?|painkillers?|paracetamol|panadol|ibuprofen|"
        r"nurofen|aspirin|antidepressants?|sleepers|sleeping aids?|insulin|"
        r"codeine|opioids?|benzos?)\b"
        r"|\b(?:pills?|tablets?|capsules?|meds|medications?|medicines?|"
        r"painkillers?|paracetamol|antidepressants?)\b.{0,60}\b(?:die|kill|"
        r"(?:not|never) wake|end (?:it|my life|things)|be fatal|be lethal|"
        r"stop (?:my )?(?:heart|breathing))\b"
        r"|\b(?:take|took|taking|swallow\w*) (?:all|the whole|a whole|every one) "
        r"(?:of )?(?:my |the )?(?:\w+ ){0,2}(?:pills?|tablets?|bottle|packet|box|"
        r"meds|medications?)\b"
        r"|\b(?:ways?|methods?|how) (?:to|of|do i|can i|could i|would i|should i|"
        r"do you|does someone|do people|would someone)\b.{0,20}\b(?:kill "
        r"(?:myself|yourself|oneself|themselves)|die|end (?:my|your|one['’]s|"
        r"their) (?:own )?life|commit suicide|hang (?:myself|yourself))\b"
        r"|\b(?:painless|quick|quickest|easiest|easy|peaceful|surest) (?:way|"
        r"method) to (?:die|go|end it)\b"
        r"|\b(?:hang|hanging|drown|drowning|poison|poisoning|shoot|shooting|"
        r"stab|stabbing|suffocat\w*|gas) myself\b"
        r"|\bjump(?:ing)? (?:off|from|in front of)\b.{0,40}\b(?:to die|and die|"
        r"end it|bridge|building|cliff|roof|balcony|train)\b"
        r"|\b(?:high|tall|far) enough to (?:kill|die)\b"
        r"|\bhow (?:high|tall|far|deep)\b.{0,60}\b(?:kill|die|fatal|lethal)\b",
        re.IGNORECASE,
    ),
    # Saying goodbye, giving things away, putting affairs in order.
    re.compile(
        r"\b(?:giv(?:e|es|ing|en)|gave|pass(?:ed|ing)? on|hand(?:ed|ing)? over) "
        r"(?:away )?(?:all |most |some |lots |a lot )?(?:of )?(?:my |our )?"
        r"(?:stuff|things|belongings|possessions|valuables|treasured \w+|"
        r"favou?rite \w+)\b"
        r"|\b(?:giv(?:e|es|ing|en)|gave) (?:away )?(?:everything|it all)\b"
        r"|\b(?:giv(?:e|es|ing|en)|gave) (?:my |all my |all of my )?\w+ away\b"
        r"|\b(?:say|says|said|saying) (?:my )?(?:last |final )?goodbyes?\b"
        r"|\b(?:goodbye|farewell|suicide|final) (?:letters?|notes?|messages?|"
        r"texts?|posts?|videos?)\b"
        r"|\b(?:putting|put|get|getting|got) (?:all )?my affairs in order\b"
        r"|\bwr(?:ite|iting|itten|ote) (?:a |my )?will\b",
        re.IGNORECASE,
    ),
    # Wanting to die, disappear or not exist.
    re.compile(
        r"\b(?:want|wanted|wanting|wish|wishing|ready|planning|plan|deserve) "
        r"(?:to )?(?:just |simply )?(?:die|be dead|not be alive|not exist|"
        r"end (?:it|things|everything))\b"
        r"|\b(?:rather|better) (?:be )?dead\b"
        r"|\bend(?:ing)? (?:it|things|everything) (?:all|for good|tonight|soon|"
        r"now|forever)\b"
        r"|\b(?:to|could|should|would|will|['’]ll|gonna|wanna|might|time|ready) "
        r"(?:just |simply |quietly |finally )?(?:disappear|vanish)\b"
        r"|\b(?:disappear|vanish)(?:ed|ing)? (?:forever|for good|permanently|"
        r"completely|from (?:everyone|everything|the world|this world))\b"
        r"|\bpermanent (?:absence|disappearance)\b"
        r"|\bleave (?:this|the) world\b"
        r"|\bnot (?:be )?(?:around|alive|here) (?:next|by|for) (?:week|month|year|"
        r"christmas|long)\b",
        re.IGNORECASE,
    ),
    # No future, no point.
    re.compile(
        r"\bno (?:future|hope)\b(?! (?:data|window|days?|weeks?|dates?|readings?|"
        r"values?)\b)"
        r"|\b(?:can['’]?t|cannot|don['’]?t|do not) see (?:a|any) (?:future|way "
        r"forward|way out)\b"
        r"|\bnothing (?:left )?to (?:look forward to|live for)\b"
        r"|\bwhat['’]?s (?:even )?the point(?: of (?:anything|it|me|trying|living))?"
        r"(?: any ?more)?\s*[?.!]*\s*$"
        r"|\b(?:is|there['’]?s|there is) no point (?:in |to )?(?:anything|any of "
        r"(?:it|this)|trying|living|going on|carrying on|me|being (?:here|alive)|"
        r"life)\b"
        r"|\b(?:life|living|everything|it all|my life|existing) (?:is|feels|seems) "
        r"(?:so |completely |totally )?(?:pointless|meaningless|hopeless)\b"
        r"|\b(?:won['’]?t|will never|isn['’]?t going to|is never going to|never "
        r"going to) get (?:any )?better\b",
        re.IGNORECASE,
    ),
    # Self-harm beyond the literal phrases above.
    re.compile(
        r"\b(?:hit|hitting|scratch\w*|bang\w*|punch\w*) myself\b"
        r"|\b(?:cut|cutting|burn|burning|scratch\w*) (?:my )?(?:arms?|wrists?|"
        r"thighs?|skin)\b"
        r"|\brelaps\w* (?:on|into|with) (?:self[- ]?harm\w*|cutting)\b",
        re.IGNORECASE,
    ),
    # Means and methods: any question about how painful, quick, lethal or
    # fatal a way of injury or death is, even as curiosity or about someone
    # else. Two halves: (a) a severity word with a violent mechanism,
    # (b) a lethality word with a medication, dose or poison. Everyday senses
    # ("hang out", "my unlocks fell", "a jump in my unlocks") are excluded.
    re.compile(
        r"^(?=.*\b(?:pain(?:ful|less)?|hurts?|hurting|quick\w*|fast\w*|instant\w*|"
        r"lethal|fatal|deadly|kills?|killing|die|dies|dying|death|survive\w*|"
        r"survivable|how long)\b)"
        r"(?=.*\b(?:bleed\w*|bled|blood loss|slit\w*|wrists?|veins?|"
        r"cut(?:s|ting)? (?:myself|yourself|themselves|himself|herself|"
        r"someone|deep\w*)|hang(?:ed|ing|s)?\b(?! out)|noose|"
        r"jump\w* (?:off|from|in front of)|fall\w* from|heights?|"
        r"(?:tall|high)\w* (?:bridge|building|cliff|roof)|bridges?|cliffs?|"
        r"rooftops?|drown\w*|suffocat\w*|strangl\w*|carbon monoxide|"
        r"exhaust fumes|shoot\w*|guns?|stab\w*|knife|knives|"
        r"(?:hit by|in front of) an? (?:train|car|truck|bus))\b)"
        r"|^(?=.*\b(?:lethal|fatal|deadly|kills?|killing|die|dies|dying|death|"
        r"survive\w*|overdos\w*|pain(?:ful|less)|stop (?:your|my|their|"
        r"someone['’]s|a person['’]s) heart|(?:not|never) wake)\b)"
        r"(?=.*\b(?:pills?|tablets?|capsules?|meds|medications?|medicines?|"
        r"painkillers?|paracetamol|panadol|acetaminophen|ibuprofen|nurofen|"
        r"aspirin|codeine|tramadol|oxycodone|morphine|fentanyl|heroin|insulin|"
        r"antidepressants?|sertraline|fluoxetine|benzos?|xanax|valium|"
        r"diazepam|sleeping (?:pills|tablets)|doses?|dosage|poison\w*|bleach|"
        r"antifreeze|toxic)\b)",
        re.IGNORECASE | re.DOTALL,
    ),
    # Policy 0.3.6: euphemisms for death or not existing, in any spelling
    # ("im", "dont"). Checked before every other route, so crisis wins even
    # when the message also names movement, unlocks or data. Everyday
    # continuations ("gone for the weekend", "wake up early", "ending things
    # with my partner") are excluded.
    # Being gone or not here, and what happens after.
    re.compile(
        r"\b(?:after|when|once|if|before) (?:i['’]?m|i am|im|i['’]?ve|i have) "
        r"(?:gone|not here|not around|no longer (?:here|around|alive)|dead|"
        r"passed(?: away)?)\b"
        r"(?!\s+(?:for|to|on|at|from|away|out|off|until|till|over|this|next|"
        r"all|by|a|an|the|back|home|in|into|during|tomorrow|today|tonight)\b)"
        r"|\b(?:i['’]ll|i will|i['’]m going to|i am going to) be gone\b"
        r"(?=\s*(?:$|[.!?,;]|(?:soon|forever|for good|anyway|now|and)\b))"
        r"|\b(?:after|when|once|if) i (?:die|pass away|pass on)\b"
        r"|\b(?:after|upon) my (?:death|passing)\b"
        r"|\bmy (?:own )?(?:funeral|last wishes|final wishes|final arrangements)\b",
        re.IGNORECASE,
    ),
    # Not waking up, sleeping forever.
    re.compile(
        r"\b(?:make sure|ensure|so that|so) (?:i|they|you|someone|people|he|she|"
        r"we|a person) (?:do ?n['’]?t|dont|do not|does ?n['’]?t|doesnt|"
        r"does not|never|won['’]?t|wont|will not) wake(?: up)?\b"
        # "up" may or may not be consumed, so the exclusion allows for it.
        r"(?!\s+(?:up\s+)?(?:early|late|at|before|until|till|in time|on time|"
        r"for|the|my|your|his|her|their|our|anyone|him|them|you|us|everyone)\b)"
        r"|\b(?:never|not|no longer|do ?n['’]?t|dont|won['’]?t|wont|can['’]?t|"
        r"cant)\b.{0,25}\bwak(?:e|ing) up "
        r"(?:again|ever|any ?more)\b"
        r"|\bstop (?:waking up|existing|being alive)\b"
        r"|\b(?:go to sleep|fall asleep|sleep|asleep|rest) (?:forever|for good|"
        r"permanently|and never wake)\b"
        r"|\beternal sleep\b",
        re.IGNORECASE,
    ),
    # Ending things.
    re.compile(
        r"\bend(?:ing)? (?:it|things|everything|it all)\b"
        r"(?!\s+(?:with|between|on|at|off|early|here|there|for (?:the|now|today)|"
        r"in|by|after|before|when)\b)"
        r"(?=\s*(?:$|[.!?,;]|(?:all|now|tonight|soon|forever|for good|today|"
        r"already)\b))"
        r"|\b(?:thinking|think|thought) (?:about|of) ending (?:it|things|"
        r"everything|my life)\b(?!\s+with)",
        re.IGNORECASE,
    ),
    # Asking what people do to die or not wake up.
    re.compile(
        r"\b(?:what|how) (?:do|did|would|can|could|does|might) (?:people|someone|"
        r"they|you|others|folks|a person|somebody)\b.{0,60}\b(?:to die|die|"
        r"(?:to )?end (?:it|things|their (?:own )?lives?)|kill themselves|"
        r"(?:not|never) wake|stop existing)\b"
        r"|\bwhen (?:they|people|you|someone) want to (?:die|end (?:it|things|"
        r"their lives?)|stop existing)\b",
        re.IGNORECASE | re.DOTALL,
    ),
)

# Policy 0.3.7: current emotional distress. A first-person statement of
# strong distress now ("I feel very depressed right now", "im really low",
# "I'm overwhelmed", "idk what to do") goes to the crisis template, checked
# with the crisis families above and before diagnosis. Written as meaning
# families, not from the client-v1 wording. It must not catch:
#   - diagnosis questions ("am I depressed?", "do I have depression?"): the
#     question word order does not match, and a statement inside a question
#     or data frame ("do you think I'm depressed?", "does my data show I'm
#     depressed") is skipped, see `_is_current_distress`;
#   - third-person or general questions ("can the app detect depression?"):
#     the subject must be the person ("I", "I'm", or a sentence that starts
#     "feeling ...");
#   - feature questions ("my unlocks are down", "I'm low on battery").
_DISTRESS_SUBJECT = (
    r"(?:\bi (?:just |really |honestly |still |kind of |kinda )?(?:feel|felt like|"
    r"am feeling|['’]m feeling|have been feeling|['’]ve been feeling|keep feeling)"
    r"|\bi['’]ve been feeling|\bi['’]m feeling"
    r"|\bi['’]m|\bi am|\bi['’]ve been|\bi have been"
    r"|^\s*(?:been |just |so |really )?feeling)"
)
_DISTRESS_INTENSIFIER = (
    r"(?:so|really|very|extremely|incredibly|completely|totally|utterly|super|"
    r"deeply|terribly|awfully|seriously|absolutely|truly|horribly|unbearably|"
    r"too|pretty|quite|such)"
)
# Strong on their own.
_DISTRESS_STRONG = (
    r"(?:depressed|hopeless|helpless|empty|numb|overwhelmed|miserable|desperate|"
    r"broken|distraught|devastated|wretched|crushed|defeated|terrible|awful|"
    r"horrible|dreadful|like i['’]m drowning|like i can['’]?t breathe|"
    r"like nothing matters)"
)
# Milder words count with an intensifier ("really low") or a "now" marker
# ("low right now").
_DISTRESS_MILD = r"(?:low|down|sad|upset|lonely|anxious|stressed|bad|rough|unhappy|scared|lost)"
_DISTRESS_NOW = r"(?:right now|at the moment|now|today|tonight|lately|these days|all the time)"
# Everyday continuations: "terrible at maths", "low on battery", "down to 3".
_DISTRESS_NOT_EMOTION = r"(?!\s+(?:at|on|of|to|than|for|in|with (?:my|the) (?:phone|app|data))\b)"
_CURRENT_DISTRESS_PATTERNS = (
    re.compile(
        _DISTRESS_SUBJECT
        + r"\s+(?:" + _DISTRESS_INTENSIFIER + r"\s+){0,2}"
        + _DISTRESS_STRONG + r"\b" + _DISTRESS_NOT_EMOTION,
        re.IGNORECASE,
    ),
    re.compile(
        _DISTRESS_SUBJECT
        + r"\s+(?:" + _DISTRESS_INTENSIFIER + r"\s+){1,2}"
        + _DISTRESS_MILD + r"\b" + _DISTRESS_NOT_EMOTION,
        re.IGNORECASE,
    ),
    re.compile(
        _DISTRESS_SUBJECT + r"\s+" + _DISTRESS_MILD + r"\s+" + _DISTRESS_NOW + r"\b",
        re.IGNORECASE,
    ),
    # Not knowing what to do about one's situation (not about the app).
    re.compile(
        # The subject may be dropped ("dunno what to do", "idk what to do").
        r"(?:\bi |^\s*)(?:really |honestly |just |genuinely )?(?:don['’]t|do not|no longer) "
        r"know what (?:to do|else to do|i (?:can|should|could|am going to|"
        r"['’]m going to|am supposed to|['’]m supposed to) do)\b"
        r"(?!\s+(?:with|about|in|on|here|next|first)\b)"
        r"|\bi(?:['’]m| am) (?:at a loss|out of options)\b",
        re.IGNORECASE,
    ),
    # Falling apart, not holding together, "what's the point" said alone.
    re.compile(
        r"\b(?:my life|everything|it all) (?:is |feels like it['’]s )?"
        r"(?:completely |totally )?falling apart\b"
        r"|(?:\bi |^\s*)can['’]?t (?:hold it together|keep it together|"
        r"get through (?:this|today|the day|the night))\b"
        r"|^\s*(?:what['’]s|what is) (?:even )?the point\s*[?.!]*\s*$",
        re.IGNORECASE,
    ),
)
# A distress statement inside a question or data frame is a different
# request ("do you think I'm depressed?", "does my data show I'm
# overwhelmed?", "what if I'm depressed?"), so it keeps its own route.
_DISTRESS_FRAME_BEFORE = re.compile(
    r"\b(?:am|do|does|did|is|are|can|could|would|will|might|should|think|thinks|"
    r"say|says|said|mean|means|show|shows|showing|suggest\w*|"
    r"indicat\w*|whether|if|wonder\w*|seem\w*|look\w*|reveal\w*|confirm\w*|"
    r"signs?|when|whenever|detect\w*|notice\w*|predict\w*)\b",
    re.IGNORECASE,
)
# Only the clause just before the distress phrase can frame it: in "Tell me a
# joke, I feel really low" the request before the comma does not.
_CLAUSE_BREAK = re.compile(r"[,:–—]|\b(?:and|but|so|though|although)\b", re.IGNORECASE)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?;])\s+|\s*\n\s*")


def _is_current_distress(text: str) -> bool:
    """True for a first-person statement of strong distress now.

    Each sentence is checked on its own; a match counts only when nothing
    before it in the same clause turns it into a question or a data frame."""

    for sentence in _SENTENCE_SPLIT.split(text):
        for pattern in _CURRENT_DISTRESS_PATTERNS:
            for match in pattern.finditer(sentence):
                clause = _CLAUSE_BREAK.split(sentence[: match.start()])[-1]
                if not _DISTRESS_FRAME_BEFORE.search(clause):
                    return True
    return False


# Policy 0.3.9: asking for help or support in any form (a crisis line,
# helpline, someone to talk to, a counsellor, where to get help) goes to the
# crisis template, checked with the crisis rules and before every other
# route, so it wins even when the message also gives an address or location
# (which the template never repeats). Written as meaning families, not from
# the v5 wording. It must not catch:
#   - advice on whether to see someone ("should I see a counsellor?"), which
#     keeps the treatment refusal;
#   - help with the app or the data ("I need help reading my unlocks",
#     "who can I talk to about my data?").
_HELP_NOT_PERSONAL = (
    # The optional "to" / "with" stops the preceding "(?: to)?" backtracking
    # past the check ("who can I talk to about my data?").
    r"(?!\s+(?:(?:to|with) )?(?:with|using|on|for|to (?:understand|read|use|interpret)|"
    r"understanding|reading|interpreting|figuring|about) (?:out )?(?:the |this |my |"
    r"these |your )?(?:app|website|site|login|account|data|unlocks?|movement|gps|"
    r"phone|questions?|charts?|graphs?|results?|numbers|answers?|study|privacy|"
    r"distance|screen|settings|mindsense)\b)"
)
_HELP_SEEKING_PATTERNS = (
    # Crisis lines, helplines and support services, named in any form.
    re.compile(
        r"\b(?:crisis|help|support|suicide|mental[- ]health|counsell?ing|emergency|"
        r"distress)[- ]?(?:lines?|numbers?|hotlines?|phone ?lines?|services?|"
        r"centres?|centers?)\b"
        r"|\bhelp ?lines?\b|\bhot ?lines?\b|\blifeline\b|\bbeyond ?blue\b"
        r"|\b13 ?11 ?14\b",
        re.IGNORECASE,
    ),
    # Finding, contacting or speaking to a counsellor or other professional.
    re.compile(
        r"\b(?:find|get|see|contact|reach|call|ring|book|speak (?:to|with)|"
        r"talk (?:to|with)|connect (?:me )?(?:with|to)|refer (?:me )?to|"
        r"recommend|suggest|need|want|looking for|look for|where|nearest|near me|"
        r"closest|local|nearby)\b.{0,40}\b(?:counsell?ors?|therapists?|"
        r"psychologists?|psychiatrists?|mental[- ]health (?:professionals?|"
        r"workers?|nurses?|clinics?|teams?|support)|crisis (?:teams?|workers?|"
        r"counsell?ors?|support)|support workers?)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    # Someone to talk to.
    re.compile(
        r"\b(?:someone|somebody|anyone|anybody|a person|a real person|a human)"
        r"(?: (?:i|i['’]d|you) (?:can|could|might|should)| to)? "
        r"(?:talk|speak|reach out|turn|vent)\b(?: to| with)?" + _HELP_NOT_PERSONAL
        + r"|\bwho (?:can|could|should|do|would) i (?:talk|speak|turn|reach out|"
        r"go|call|ring|vent)\b(?: to| with)?" + _HELP_NOT_PERSONAL,
        re.IGNORECASE,
    ),
    # Where or how to get help or support, and asking for it outright.
    re.compile(
        r"\b(?:where|how|who)\b.{0,25}\b(?:get|find|go for|go to for|look for|"
        r"seek|access|turn (?:to )?for|reach out for|ask for|call for)"
        r" (?:some |any |more |real |professional |mental[- ]health |emotional |"
        r"urgent |immediate |proper )?(?:help|support)\b" + _HELP_NOT_PERSONAL
        + r"|\b(?:i (?:really |just |urgently )?need|i want|i['’]d like|can i get|"
        r"can you get me|please get me|i['’]m looking for|i am looking for) "
        r"(?:some |urgent |immediate |professional |real )?(?:help|support)\b"
        + _HELP_NOT_PERSONAL,
        re.IGNORECASE | re.DOTALL,
    ),
)
# Asking whether to see someone is advice; it keeps the treatment refusal.
_HELP_ADVICE_FRAME = re.compile(
    r"\b(?:should i|do i need to|would it help (?:me )?to|is it worth|"
    r"would you recommend i|do you think i should)\b",
    re.IGNORECASE,
)


def _is_help_seeking(text: str) -> bool:
    """True for a request for a crisis line, support or someone to talk to."""

    lines, professional, talk, get_help = (
        pattern.search(text) for pattern in _HELP_SEEKING_PATTERNS
    )
    if lines or talk or get_help:
        return True
    return bool(professional) and not _HELP_ADVICE_FRAME.search(text)


# Policy 0.3.5: a named mental-health or neurodevelopmental condition asked
# about the user is a diagnosis request, even when the question also names a
# feature ("does my unlock pattern look like ADHD?"). Checked after the other
# prohibited categories, so treatment, risk and cause keep their own refusal.
_NAMED_CONDITION = re.compile(
    r"\b(?:depression|depressive|anxiety|adhd|attention[- ]deficit|bipolar|"
    r"manic|mania|ptsd|post[- ]traumatic|ocd|obsessive[- ]compulsive|"
    r"eating disorders?|anorexi\w*|bulimi\w*|binge[- ]eating|autism|autistic|"
    r"asperger\w*|schizo\w*|psychosis|psychotic|borderline|bpd|"
    r"personality disorder|panic disorder|panic attacks?|agoraphobi\w*|"
    r"phobias?|insomnia|dyslexi\w*|tourette\w*|dementia|seasonal affective|"
    r"neurodivergen\w*|neurodevelopmental|mental (?:illness|disorder|health "
    r"condition)|\w+ disorder)\b",
    re.IGNORECASE,
)
_SELF_REFERENCE = re.compile(
    r"\b(?:i|i['’]m|im|i['’]ve|i['’]d|me|my|myself|mine)\b", re.IGNORECASE
)
# Mood words are not condition names, but asking the data to show them is
# still diagnosis ("do my unlocks show I'm depressed?").
_SELF_ASSESSMENT_FROM_DATA = re.compile(
    r"\b(?:show|shows|showing|mean|means|suggest\w*|indicat\w*|look(?:s)? like|"
    r"signs? (?:of|that)|reveal\w*|tell (?:you|me)|say|says|consistent with|"
    r"evidence (?:of|that))\b.{0,60}\b(?:i(?:['’]m| am| was)|i['’]ve been|"
    r"i have been|me)\b.{0,20}\b(?:depressed|anxious|unwell|mentally ill|ill|"
    r"sick)\b",
    re.IGNORECASE,
)


def _is_named_condition_request(question: str) -> bool:
    return bool(
        _NAMED_CONDITION.search(question) and _SELF_REFERENCE.search(question)
    ) or bool(_SELF_ASSESSMENT_FROM_DATA.search(question))

_PROHIBITED_PATTERNS: tuple[
    tuple[RequestCategory, str, tuple[re.Pattern[str], ...]], ...
] = (
    (
        RequestCategory.PROMPT_INJECTION,
        "prompt_injection_detected",
        (
            re.compile(
                r"\bignore (?:all |the |your |any )?(?:previous|prior) instructions\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:reveal|show|print) (?:me )?(?:the |your )?(?:system|developer) prompt\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:bypass|disable|override) (?:the )?(?:safety|guardrail|policy)\b",
                re.IGNORECASE,
            ),
            # Policy 0.3.4: any determiner before the rules ("your safety
            # rules", "all content filters"), and more verbs.
            re.compile(
                r"\b(?:bypass|disable|override|ignore|turn off|switch off|get around|"
                r"break|remove|forget|drop) (?:all |the |your |any |these |those |of "
                r"your )?(?:own )?(?:safety |content |usual )?(?:rules|restrictions|"
                r"guard ?rails?|filters?|policies|policy|limits|limitations|"
                r"guidelines|instructions|programming)\b",
                re.IGNORECASE,
            ),
            # Persona and jailbreak framings ("you are now X with no content
            # policy", "DAN", "developer mode"). "Pretend you're a
            # psychiatrist" stays a diagnosis request (dev Q42).
            re.compile(
                r"\byou are (?:now|no longer)\b|\bfrom now on,? you(?: are|['’]re| will)\b"
                r"|\b(?:with|has|have) no (?:content )?(?:policy|policies|rules|"
                r"restrictions|filters|limits|guidelines)\b"
                r"|\bwithout (?:any )?(?:content )?(?:policy|policies|rules|restrictions|"
                r"filters|limits|guidelines)\b"
                r"|\b(?:developer|god|unrestricted|jailbreak) mode\b|\bjailbr(?:ea|o)k\w*\b",
                re.IGNORECASE,
            ),
            re.compile(r"\bDAN\b"),
            # Policy 0.3.8: requests to show, print or reveal hidden or system
            # instructions, in any wording.
            re.compile(
                r"\b(?:show|print|reveal|display|output|repeat|recite|tell me|"
                r"give me|share|list|dump|paste|copy|leak|expose|what (?:are|were))"
                r"\b.{0,40}\b(?:hidden|secret|internal|system|initial|original|"
                r"underlying|developer|pre-?set|built-?in|behind-the-scenes|"
                r"confidential)\b.{0,20}\b(?:instructions?|prompts?|rules|"
                r"guidelines|directives|configuration|config|programming)\b"
                r"|\b(?:instructions?|prompts?|rules) (?:that )?you (?:were|have "
                r"been|got|are) (?:given|told|set up with|programmed with)\b"
                r"|\b(?:show|print|reveal|display|repeat|tell me|give me|share) "
                r"(?:me )?your (?:prompt|instructions|programming)\b",
                re.IGNORECASE | re.DOTALL,
            ),
        ),
    ),
    (
        RequestCategory.DIAGNOSIS_SEEKING,
        "diagnosis_request_detected",
        (
            re.compile(r"\b(?:diagnose|diagnosis)\b", re.IGNORECASE),
            re.compile(
                r"\b(?:do|could) i have (?:depression|anxiety|a mental (?:illness|health condition))\b",
                re.IGNORECASE,
            ),
            re.compile(r"\bam i (?:depressed|anxious|mentally ill)\b", re.IGNORECASE),
            re.compile(
                r"\bdo you think i(?: am|['’]m) (?:depressed|anxious|mentally ill)\b",
                re.IGNORECASE,
            ),
            # Policy 0.3.2 (ME-P01 F4 near-variant).
            re.compile(
                r"\bdo you think i (?:have|might have) (?:depression|anxiety|"
                r"a mental (?:illness|health condition))\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:can|could) you (?:tell|determine|assess) (?:if|whether) "
                r"i(?: am|'m) (?:becoming |getting )?(?:depressed|anxious|mentally ill)\b",
                re.IGNORECASE,
            ),
            re.compile(r"\bdoes (?:this|that).{0,80}\bmean i have\b", re.IGNORECASE),
            # Policy 0.3.4: qualified self-assessment ("clinically anxious",
            # "actually depressed"), named conditions and asking what is wrong.
            re.compile(
                r"\b(?:am i|i['’]?m|i am|is it that i(?:['’]m| am)) (?:clinically|"
                r"medically|really|actually|seriously|officially|technically) "
                r"(?:depressed|anxious|bipolar|mentally ill|unwell|ill|sick|"
                r"disordered|traumati[sz]ed)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:what['’]?s|what is|is (?:there )?(?:something|anything)) wrong "
                r"with me\b"
                r"|\b(?:do|could|might) i (?:have|suffer from) (?:an? )?"
                r"(?:anxiety|depressive|mood|panic|eating|personality|bipolar|"
                r"mental|psychological|psychiatric) (?:disorder|condition|illness)\b"
                r"|\b(?:do|could|might) i have (?:adhd|ptsd|ocd|bipolar|bpd|"
                r"autism|an eating disorder|burnout|clinical depression)\b",
                re.IGNORECASE,
            ),
            # Policy 0.3.3 (dev Q38): asking the data to confirm a named
            # condition, e.g. "My doctor says I'm depressed. Does my data
            # confirm it?"
            re.compile(
                r"^(?=.*\b(?:depress\w*|anxi\w*|bipolar|adhd|ptsd|ocd|"
                r"mental (?:illness|health condition|disorder))\b)"
                r".*\b(?:confirm|prove|back (?:it|that|this) up|agree|consistent with)",
                re.IGNORECASE,
            ),
            # Policy 0.3.8: asking whether the person's own data means
            # something about their mental state ("does that mean I'm getting
            # worse?", "...my mental health is declining?", "...something is
            # wrong with me?"). A forecast ("does that mean I'm going to get
            # worse?") is left to the risk family; "prove" stays causal.
            re.compile(
                r"\b(?:mean|means|meant|say|says|suggest\w*|indicat\w*|show|shows|"
                r"showing|tell|tells|signs? (?:of|that)|point(?:s|ing)? to|"
                r"reflect\w*)\b"
                r"(?:(?!\b(?:going to|gonna|will|about to)\b).){0,60}?"
                r"(?:\b(?:i(?:['’]m| am| was)|im|i['’]?ve been|i have been)\b"
                r"(?:(?!\b(?:going to|gonna|will|about to)\b).){0,25}?"
                r"\b(?:getting worse|worse(?! (?:at|in|with|about) )|declining|"
                r"deteriorating|going downhill|not (?:okay|ok|well|coping|doing "
                r"(?:well|ok|okay))|struggling|unwell|unstable|mentally|in a bad "
                r"(?:way|place)|falling apart)\b"
                r"|\bmy (?:mental health|mental state|mind|head ?space|well[- ]?being|"
                r"mood|state of mind)\b.{0,20}?\b(?:declining|getting worse|worse|"
                r"deteriorating|going downhill|slipping|suffering)\b"
                r"|\b(?:something|anything)(?: is|['’]s)? (?:wrong|off) with me\b)",
                re.IGNORECASE,
            ),
        ),
    ),
    (
        # Policy 0.3.3 (dev Q35/Q39): MindSense gives no clinical or
        # mental-health score. Checked before scope so the PHQ-4 domain word
        # no longer routes to the feature clarification.
        RequestCategory.CLINICAL_SCORE_REQUEST,
        "clinical_score_request_detected",
        (
            re.compile(r"\b(?:phq|gad)[- ]?\d+\b", re.IGNORECASE),
            re.compile(
                r"\b(?:mental[- ]health|depression|anxiety|mood|stress|well[- ]?being) "
                r"(?:score|rating)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:score|rate) my (?:mental health|mood|depression|anxiety)\b",
                re.IGNORECASE,
            ),
        ),
    ),
    (
        RequestCategory.TREATMENT_ADVICE_SEEKING,
        "treatment_advice_request_detected",
        (
            re.compile(
                r"\bwhat (?:medication|medicine|treatment|therapy) should i\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\bshould i (?:start|stop|take|change) (?:medication|medicine|treatment|therapy)\b",
                re.IGNORECASE,
            ),
            re.compile(r"\b(?:prescribe|prescription)\b", re.IGNORECASE),
            # Policy 0.3.3 (dev Q31/Q40): whether to see a professional, or
            # how to improve mood, is advice MindSense cannot give.
            re.compile(
                r"\bshould i (?:see|talk to|speak to|visit|go to|get) (?:a |an |my )?"
                r"(?:therapist|psychologist|psychiatrist|counsell?or|doctor|gp|"
                r"professional|mental[- ]health professional)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\bhow (?:can|do|could|should) i (?:improve|boost|fix|lift|raise|help) "
                r"my (?:mood|mental health|well[- ]?being|anxiety|depression|stress)\b",
                re.IGNORECASE,
            ),
            # Policy 0.3.4: plans and recommendations ("suggest a coping plan").
            re.compile(
                r"\b(?:recommend|suggest|prescribe|give me|make me|design|create|write) "
                r"(?:me )?(?:a |an |some |my )?(?:personal(?:ised|ized)? )?"
                r"(?:treatment|therapy|medication|medicine|recovery|care|coping|"
                r"self[- ]care|wellness|mental[- ]health) "
                r"(?:plan|options?|strateg(?:y|ies)|programme|program|regime|routine)?\b"
                r"|\btreatment (?:plan|options?)\b",
                re.IGNORECASE,
            ),
            re.compile(
                # Emotional or clinical goals only: "what can I do to get more
                # movement?" is a feature question and stays in scope.
                r"\bwhat (?:should|can|could|do) i (?:do|try|take) (?:to|so (?:that )?i) "
                r"(?:feel|be (?:happier|calmer|less|more|better|okay|ok)|"
                r"get (?:better|over|rid of|through)|stop (?:feeling|being|worrying|"
                r"panicking|crying)|cope|calm down|relax|manage (?:my )?(?:stress|"
                r"anxiety|mood|feelings)|reduce (?:my )?(?:stress|anxiety)|beat|"
                r"overcome|deal with (?:my )?(?:stress|anxiety|feelings|this)|"
                r"sleep better)\b"
                r"|\bhow (?:can|do|could|should) i (?:feel|be) (?:less|more|better)\b"
                r"|\bhow (?:can|do|could|should) i get better\b"
                r"|\bhow (?:can|do|could|should) i (?:stop|cope with|deal with|manage|"
                r"beat|overcome|reduce|treat|cure) (?:my |the |this )?(?:anxiety|"
                r"depression|stress|panic|sadness|low mood|feelings?|symptoms|"
                r"mental health)\b",
                re.IGNORECASE,
            ),
            # Policy 0.3.5: treatment by meaning. A medication, supplement or
            # therapy word together with any advice or change cue.
            re.compile(
                r"^(?=.*\b(?:medications?|medicines?|meds|pills?|tablets?|"
                r"antidepressants?|ssris?|sertraline|fluoxetine|escitalopram|"
                r"citalopram|lexapro|zoloft|prozac|venlafaxine|ritalin|adderall|"
                r"stimulants?|lithium|benzos?|xanax|melatonin|supplements?|"
                r"vitamins?|therapy|therapist|counsell?(?:ing|or)|cbt|psychiatrist|"
                r"psychologist|treatment)\b)"
                r".*\b(?:should|would|could|will|can|do i need|help|helps|helping|"
                r"recommend\w*|suggest\w*|advise|advice|try|start|stop|quit|take|"
                r"taking|increase|decrease|reduce|raise|up|lower|change|switch|"
                r"dose|dosage|worth it|work for me|better)\b",
                re.IGNORECASE | re.DOTALL,
            ),
            # "Should I see / ask / start ...?" and "what should I do about".
            re.compile(
                r"\bshould i (?:see|get|go to|talk to|speak to|ask|book|try|start|"
                r"stop|take|change|increase|reduce|lower|up|switch|quit|come off|"
                r"seek|get help|call)\b"
                r"|\bwhat (?:should|can|could|do|would you suggest) i (?:do|try) "
                r"about\b"
                r"|\bwhat (?:should|can|could) i do (?:now|next|to fix)\b"
                r"|\bhow (?:do|can|should|could) i (?:treat|fix|cure|get help|get "
                r"treatment|get (?:some )?support)\b",
                re.IGNORECASE,
            ),
        ),
    ),
    (
        RequestCategory.RISK_PREDICTION_SEEKING,
        "risk_prediction_request_detected",
        (
            re.compile(
                r"\b(?:predict|calculate|estimate) my (?:mental health )?risk\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\bwhat (?:is|are) my (?:odds|risk|chances) of\b", re.IGNORECASE
            ),
            re.compile(
                r"\bwill i (?:become|get|develop) "
                r"(?:depressed|depression|anxious|anxiety|a mental illness)\b",
                re.IGNORECASE,
            ),
            # Policy 0.3.4: forecasts about the person's mental state and
            # questions about their own risk level.
            re.compile(
                r"\b(?:will|is|are|am|could|might) (?:my |i )?(?:mental health|mood|"
                r"anxiety|depression|stress|well[- ]?being|symptoms|condition|"
                r"mental state|state of mind|i)? ?(?:going to |likely to |about to )?"
                r"(?:get worse|get better|deteriorate|decline|worsen|improve|relapse|"
                r"break down|crash|spiral)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:am i|are you saying i(?:['’]m| am)|is there a|what(?:['’]s| is) "
                r"the) (?:at |in )?(?:high |low |any |serious )?(?:risk|chance|"
                r"likelihood|danger|odds) (?:of|for)\b"
                r"|\bam i (?:at|in) (?:high |low |any |serious )?(?:risk|danger)\b"
                r"|\b(?:risk|chance|likelihood|odds) of (?:a |me having a |having a |me )?"
                r"(?:breakdown|relapse|burnout|crisis|depression|anxiety|getting worse)\b"
                r"|\bam i (?:going|likely|about) to (?:have a breakdown|break down|"
                r"relapse|get worse|crash|burn out)\b",
                re.IGNORECASE,
            ),
            # Policy 0.3.5: risk and forecasts by meaning ("will I", "chance
            # of", "likely to", "going to get"). Questions about seeing a
            # baseline or comparison are app questions, not forecasts.
            re.compile(
                r"\bwill i\b(?! (?:be able to )?(?:see|get|have) (?:a |my |the )?"
                r"(?:baseline|comparison|results?|answer)\b)"
                r"|\b(?:chances?|odds|probability|likelihood|percentage|risk) "
                r"(?:of|that|for)\b"
                r"|\b(?:how )?likely (?:to|is it|am i|that|is that)\b"
                r"|\b(?:am i|is (?:it|this|that|my \w+(?: \w+)?)|are (?:my \w+|things)|"
                r"will (?:it|things|this|my \w+(?: \w+)?)) going to (?:get|be|become|"
                r"end up|turn)\b"
                r"|\bgoing to get (?:worse|better|bad|harder|easier|sick|ill|"
                r"depressed|anxious)\b"
                r"|\b(?:predict|forecast)\w*\b",
                re.IGNORECASE,
            ),
            # Policy 0.3.8: future outcomes in any wording ("am I going to
            # have a bad week?", "will next month be hard?", "a rough time
            # ahead"). Asking whether a result will be shown is not a forecast.
            re.compile(
                r"\b(?:am i|are we|are things|is everything|is life) (?:going to|"
                r"gonna|about to|likely to|set to) (?!(?:be able to )?(?:see|get|"
                r"have|receive|view) (?:a |an |my |the |any )?(?:baseline|"
                r"comparison|results?|answers?|summary|response)\b)\w+"
                r"|\b(?:is|will) (?:it|this|that|things|life|everything) gonna\b"
                r"|\bwill (?:next|the next|the coming|this coming|coming|tomorrow|"
                r"tonight|my next|the rest of)\b(?: \w+){0,3} be\b"
                r"|\b(?:bad|good|rough|hard|tough|difficult|better|worse|dark|low) "
                r"(?:day|days|week|weeks|month|months|year|term|semester|time|times|"
                r"patch|stretch|period) (?:ahead|to come|in store|coming up)\b"
                r"|\bwhat (?:will|is going to|is gonna) happen (?:to me|next|in the "
                r"future)\b",
                re.IGNORECASE,
            ),
        ),
    ),
    (
        RequestCategory.CAUSAL_INFERENCE_SEEKING,
        "causal_inference_request_detected",
        (
            re.compile(
                r"\b(?:did|does|can|could|will).{0,80}\b(?:cause|caused|make|made|lead to|result in)\b",
                re.IGNORECASE,
            ),
            re.compile(r"\bwhy did.{0,80}\b(?:cause|make)\b", re.IGNORECASE),
            re.compile(r"\bis .{0,80}\bthe (?:reason|cause)\b", re.IGNORECASE),
            # Policy 0.3.3 (dev Q29/Q47): "because"/"due to" questions and
            # requests for proof; needed once a feature word alone is in scope.
            # Any "because"/"due to" refuses (fail closed): MindSense never
            # confirms or rejects a stated cause.
            re.compile(r"\b(?:because|due to)\b", re.IGNORECASE),
            # Policy 0.3.5: the same fail-closed rule for "is that why",
            # "the reason", "is it from/down to/linked to", in any wording.
            re.compile(
                r"\b(?:is|was|could|might|would|can) (?:it|that|this|these|those) "
                r"(?:be )?(?:the (?:reason )?)?why\b"
                r"|\b(?:that['’]?s|that is|this is|this['’]s|is that|is this|is it) "
                r"(?:the reason )?why\b"
                r"|\b(?:the )?reasons? (?:why |that )?(?:i|i['’]ve|i['’]m|my|me)\b"
                r"|\breasons? (?:for|behind) (?:my|the change|this|that|these|it)\b"
                r"|\b(?:is|was|are|were) (?:it|that|this|these|those) (?:from|down "
                r"to|caused by|related to|linked to|connected to|tied to|a result "
                r"of|the result of|because of|thanks to)\b"
                r"|\b(?:is|was|are|were) (?:my|this|that|it|these) .{0,60}\b(?:linked|"
                r"related|connected|tied|attributable) to\b",
                re.IGNORECASE,
            ),
            # Policy 0.3.5: "why" about the person's own movement or unlocks,
            # in every word form (moving, moved, movement; unlocking,
            # unlocks). Questions about the baseline or the evidence itself
            # ("why can't you compare with my baseline?") are not causal.
            re.compile(
                r"^(?!.*\b(?:baseline|compar\w*|enough (?:data|history)|"
                r"uncertain\w*|evidence)\b)"
                r".*\bwhy\b(?: (?:have|has|had|am|is|are|was|were|do|does|did|"
                r"would|might|could|can|should)(?:n['’]?t)?)? (?:i|i['’]ve|i['’]m|"
                r"my|me)\b.{0,80}\b(?:mov(?:e|es|ed|ing)|movements?|mobility|"
                r"travel\w*|distance|gps|unlock(?:s|ed|ing)?|pick(?:s|ed|ing)? up|"
                r"phone|screen time|go(?:es|ing)? out|went out|leav(?:e|es|ing) "
                r"(?:the house|home)|stay(?:s|ed|ing)? (?:in|home|inside)|active)\b",
                re.IGNORECASE | re.DOTALL,
            ),
            re.compile(r"\bprov(?:e|es|ed|ing)\b|\bproof\b", re.IGNORECASE),
            # Policy 0.3.4: "root cause", "what is causing/behind", "why is X
            # making me Y", "X is making me anxious".
            re.compile(
                r"\b(?:root )?caus(?:e|es|ed|ing) of\b|\broot cause\b"
                r"|\bwhat(?:['’]s| is| are| has been| have been) (?:causing|behind|"
                r"driving|triggering|making|pushing)\b"
                r"|\bwhy (?:is|are|does|do|did|was|were|am)\b.{0,80}\b(?:making|made|"
                r"causing|caused|giving|leaving|turning)\b"
                r"|\b(?:is|are|was|were|keeps?) (?:making|leaving) me (?:feel )?"
                r"(?:anxious|sad|depressed|stressed|tired|lonely|worse|unhappy|low|"
                r"down|nervous|upset|on edge)\b",
                re.IGNORECASE,
            ),
        ),
    ),
    (
        RequestCategory.SENSITIVE_DATA_REQUEST,
        "sensitive_data_request_detected",
        (
            re.compile(
                r"\b(?:show|reveal|export|give me) (?:the )?(?:raw )?(?:gps|location) (?:data|coordinates|history)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:show|reveal|export|give me) (?:the )?(?:participant|subject|user) (?:id|identifier)\b",
                re.IGNORECASE,
            ),
            # Policy 0.3.3 (dev Q50): only the person's own data is described.
            re.compile(
                r"\b(?:another|other|different) (?:participant|person|user|student)s?\b"
                r"|\bother people\b|\b(?:someone|somebody|everyone|anyone) else\b",
                re.IGNORECASE,
            ),
            # Policy 0.3.8: a home or street address, or where the person
            # sleeps, lives or spends the night. Only movement distance is
            # described, never places.
            re.compile(
                r"\b(?:my|the|your|an?|exact|home|street|house|postal|residential|"
                r"mailing) (?:(?:home|street|house|postal|residential|exact|"
                r"mailing) )?address(?:es)?\b"
                r"|\bwhere (?:do |did |have )?i (?:been )?(?:sleep|slept|sleeping|"
                r"live|lived|living|stay|stayed|staying|reside|spend|spent|spending)\b"
                r"|\bwhere (?:i|i['’]ve|i['’]m|im) (?:sleep|slept|sleeping|live|"
                r"living|stay|staying|spend|spending)\b"
                r"|\bwhere(?:['’]s| is| are) (?:my )?(?:home|house|place|flat|"
                r"apartment|dorm|room|bed)\b"
                r"|\b(?:locate|find|pinpoint|identify|work out|figure out) (?:where )?"
                r"(?:my )?(?:home|house|flat|apartment|dorm)\b",
                re.IGNORECASE,
            ),
        ),
    ),
)

# Policy 0.3.2 (ME-P01 F1): a whole-question "what can you do?" request gets
# the deterministic capability template instead of the off-topic refusal. It
# keeps the REFUSE disposition so no participant data is loaded and no model
# or context is invoked. Anchored to the full question so evidence questions
# such as "what can you tell me about my unlocks?" are not captured.
_CAPABILITY_PATTERNS = (
    re.compile(
        r"^\s*(?:(?:hi|hello|hey)[\s,!.]+)?"
        r"(?:what (?:can|could) you (?:help (?:me )?with|do(?: for me)?)|"
        r"what do you do|how (?:can|could) you help(?: me)?|"
        r"what are you (?:able to do|for)|what can i ask(?: you)?)"
        r"\s*[?.!]*\s*$",
        re.IGNORECASE,
    ),
    # Policy 0.3.8: "what (sorts of / kinds of) questions can I ask?",
    # also anchored to the whole question.
    re.compile(
        r"^\s*(?:(?:hi|hello|hey)[\s,!.]+)?"
        r"(?:so,? |ok(?:ay)?,? )?what (?:(?:sorts?|kinds?|types?|sort|kind|type) "
        r"of )?(?:questions?|things|stuff) (?:can|could|should|may|do|am) i "
        r"(?:allowed to )?ask(?: you)?(?: about)?"
        r"(?: here| in (?:this|the) app| mindsense)?"
        r"\s*[?.!]*\s*$",
        re.IGNORECASE,
    ),
)

# Policy 0.3.3 (dev Q9/Q10/Q19/Q20): questions about the app itself get a
# fixed informational text. Like the capability route they keep the REFUSE
# disposition, so no participant data is loaded and no model is called. The
# reason code selects the template in SLMService.
_APP_INFORMATION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    # Policy 0.3.9: whether MindSense tracks the person in the background or
    # uses the camera or microphone, listens or records. Answered by
    # `app_info_sensors`. Tracking words count only with a background cue or
    # a non-feature object, so "is the app tracking my unlocks?" and "does
    # listening to music change my unlocks?" keep their evidence route.
    (
        "app_info_sensors",
        re.compile(
            r"\b(?:cameras?|webcams?|microphones?|mic)\b"
            r"|\b(?:you|mindsense|the app|this app|the website|it|my phone|the phone|"
            r"this phone|anyone|someone|they)\b(?: \w+){0,3}? (?:secretly |always |"
            r"constantly |still |actually )?(?:listen(?:s|ing)?(?: to me| in)?\b"
            r"|eavesdrop\w*|overhear\w*|spy(?:ing)? on|hear(?:s|ing)? (?:me|what i|my)"
            r"|record(?:s|ing)? (?:me|us|my (?:voice|conversations?|calls?|audio|"
            r"screen|face|surroundings|location)|what i|audio|sound|video|"
            r"everything|anything))\b"
            r"|\b(?:track\w*|monitor\w*|watch\w*|record\w*|collect\w*|log(?:s|ging)?|"
            r"follow\w*|spy\w*|listen\w*)\b.{0,40}\b(?:in the background|"
            r"background|all the time|24/7|around the clock|constantly|"
            r"continuously|secretly|without (?:me|my) know\w*|when i(?:['’]m| am) "
            r"not using|while i(?:['’]m| am) not using|behind my back)\b"
            r"|\bbackground (?:tracking|monitoring|recording|data collection|"
            r"listening|location)\b"
            r"|\b(?:are|is|do|does|will|can|could)\b (?:you|mindsense|the app|this "
            r"app|it|my phone)(?: \w+){0,2}? (?:track\w*|monitor\w*|watch\w*|"
            r"follow\w*) (?:me|us|where i (?:go|am)|my (?:location|whereabouts|"
            r"every move|movements|phone|messages|calls|browsing|apps|"
            r"conversations)|everything)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "app_info_data_storage",
        re.compile(
            r"\b(?:is|are) my (?:data|information|questions?|chats?|answers?) "
            r"(?:stored|saved|kept|shared|sent|uploaded)\b"
            r"|\bwhere (?:is|are) my (?:data|information) (?:stored|kept|saved|sent)\b"
            r"|\b(?:do|does) (?:you|mindsense|the app|this app) (?:store|save|keep|share|"
            r"send|upload) my (?:data|information|questions?|chats?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "app_info_data_use",
        re.compile(
            r"\bwhat (?:data|information|sensors?) (?:do|does) (?:you|mindsense|the app|"
            r"this app) (?:use|collect|look at|need)\b"
            r"|\bwhat data is used\b",
            re.IGNORECASE,
        ),
    ),
    # Policy 0.3.7: which dates or period the app has data for, and which
    # days were or were not collected. Answered by the data-use template (a
    # recent window of about two weeks, compared with earlier history); no
    # dates or day lists are given.
    (
        "app_info_data_use",
        re.compile(
            r"\b(?:which|what) (?:time )?(?:period|periods|dates?|days?|months?|"
            r"time ?frames?|time ?range|range of dates|weeks?)\b.{0,40}\b(?:do|does|"
            r"did) (?:you|mindsense|the app|this app) (?:have|hold|keep|store|"
            r"collect|use|cover)\b"
            r"|\b(?:how much|how long|how far back|how many days of) (?:data |"
            r"history |information )?(?:do|does) (?:you|mindsense|the app|this "
            r"app) (?:have|hold|keep|go back)\b"
            r"|\b(?:what|which) (?:sensors?|data) (?:do|does) (?:you|mindsense|the "
            r"app|this app) have\b"
            r"|\b(?:days?|dates?|when) (?:when )?(?:my |the )?data (?:was|were|is|"
            r"wasn['’]?t|weren['’]?t|was not|were not) (?:collected|recorded|"
            r"missing|tracked)\b"
            r"|\b(?:which|what) (?:days?|dates?)\b.{0,30}\bdata\b.{0,20}"
            r"\b(?:collected|recorded|tracked|missing)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    # Policy 0.3.7: requests to delete, remove or erase the person's data.
    # The storage template says MindSense cannot delete study data.
    (
        "app_info_data_storage",
        re.compile(
            r"\b(?:delete|remove|erase|wipe|destroy|purge|get rid of)\b.{0,30}"
            r"\b(?:my|all my|all of my|our)\b.{0,20}\b(?:data|information|info|"
            r"records?|history|recordings?|readings?|details)\b"
            r"|\b(?:my|all my) (?:data|information|records?|history) "
            r"(?:be )?(?:deleted|removed|erased|wiped)\b"
            r"|\b(?:how (?:do|can) i|can i|can you|could you|please) (?:have |get )?"
            r"(?:my )?(?:data|information|records?) (?:deleted|removed|erased)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "app_info_uncertain_evidence",
        re.compile(
            r"\bwhat (?:does|do|is) [\"“'‘]?uncertain(?:ty)?(?: evidence)?[\"”'’]?"
            r"(?: mean)?\s*[?.!]*\s*$",
            re.IGNORECASE,
        ),
    ),
    (
        "app_info_baseline_unavailable",
        re.compile(
            r"\bwhy (?:can['’]?t|cannot|can not|couldn['’]?t|won['’]?t|don['’]?t|"
            r"didn['’]?t) you compare\b"
            r"|\bwhy (?:is|isn['’]?t) (?:there (?:no|not a) )?(?:my )?baseline\b",
            re.IGNORECASE,
        ),
    ),
)


def app_information_reason(question: str) -> str | None:
    """Reason code of the matching app-information question, if any."""

    for reason_code, pattern in _APP_INFORMATION_PATTERNS:
        if pattern.search(question):
            return reason_code
    return None


# The two-part rule is intentionally conservative: ordinary questions need a
# MindSense feature plus evidence-analysis intent. Short contextual questions
# that are meaningful in an evidence view are listed separately. Unmatched or
# ambiguous requests fail closed without invoking the model.
_DOMAIN_PATTERNS = (
    re.compile(
        r"\b(?:gps|movement|mobility|unlock(?:s|ed|ing)?|phq[- ]?4|"
        r"well[- ]?being|behavio(?:u)?r)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bphone (?:use|usage|activity|unlock(?:s|ed|ing)?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:tracked|location) (?:data|pattern|history)\b|\bscreen time\b",
        re.IGNORECASE,
    ),
)
_EVIDENCE_INTENT_PATTERNS = (
    re.compile(
        r"\b(?:baseline|pattern|history|evidence|data|score|trend|uncertainty|"
        r"relationship|association|correlation|chang(?:e|ed|ing)|different|"
        r"compare|comparison|higher|lower|usual|normal|unusual|frequent|"
        r"conclude|enough|observed|window)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bhow (?:was|is|has) my\b", re.IGNORECASE),
)
_CONTEXTUAL_IN_SCOPE_PATTERNS = (
    re.compile(r"\bwhat changed\b", re.IGNORECASE),
    # Policy 0.3.8: "has anything (about me) changed?" names no feature, so
    # preflight asks "movement or phone unlocks?" instead of refusing it.
    re.compile(
        r"\b(?:has|have) (?:anything|something) (?:about me |with me |for me |"
        r"in my (?:routine|data|patterns?|behaviou?r|activity|habits) )?"
        r"(?:changed|been different|shifted)\b"
        r"(?=\s*(?:[?.!]|$|compared|than|from (?:usual|normal|before)|lately|"
        r"recently|since|for me|about me|with me|at all|much|\w+ly\b))"
        r"|\bis (?:anything|something) different (?:about me|with me|for me|"
        r"lately|recently|from usual|than usual|compared)\b"
        r"|\bhave i changed\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bhow am i doing\b", re.IGNORECASE),
    # Policy 0.3.3 (dev Q17): names no single feature, so preflight asks
    # which feature to use instead of refusing it as off-topic.
    re.compile(r"\bhow active (?:have|had|was|am) i\b", re.IGNORECASE),
    re.compile(
        r"\b(?:describe|explain|compare) my (?:recent |tracked )?activity\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bis this (?:higher|lower|different) (?:or (?:higher|lower) )?"
        r"than (?:normal|usual) for me\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bwhat uncertainty should i keep in mind\b", re.IGNORECASE),
    re.compile(r"\bis there enough (?:data|history)\b", re.IGNORECASE),
    re.compile(
        r"\bwhat does the word (?:depressed|anxious|depression|anxiety) mean\b",
        re.IGNORECASE,
    ),
)


# Which statistics-side feature (backend.statistics.participant_evidence's
# `_FEATURES` dict keys) a question is actually about. Kept separate from
# the in/out-of-scope patterns above: those decide WHETHER to answer, this
# decides WHICH feature's evidence packet to answer from. Before this
# existed, `/respond` always answered from `gps_distance` regardless of
# what was asked (see backend/api/app.py's `RespondRequest.feature_id`
# default) — an unlock-related question silently got a GPS answer.
DEFAULT_FEATURE_ID = "gps_distance"

_UNLOCK_FEATURE_PATTERNS = (
    re.compile(r"\bunlock(?:s|ed|ing)?\b", re.IGNORECASE),
    re.compile(r"\bphone (?:use|usage|activity)\b", re.IGNORECASE),
    re.compile(r"\bscreen time\b", re.IGNORECASE),
    re.compile(r"\bpick(?:s|ed|ing)?[- ]?up(?:s)?\b", re.IGNORECASE),
    # Policy 0.3.3 (dev Q16): everyday wording for phone use.
    re.compile(r"\b(?:on|use|used|using) my phone\b", re.IGNORECASE),
)

_GPS_NAMED_FEATURE_PATTERNS = (
    re.compile(r"\btravel(?:l?ed|ling|s)?\b", re.IGNORECASE),
    re.compile(r"\bdistance\b", re.IGNORECASE),
    re.compile(r"\bmovement\b", re.IGNORECASE),
    re.compile(r"\bmobility\b", re.IGNORECASE),
    # Policy 0.3.3 (dev Q1/Q15): everyday wording for distance moved.
    re.compile(r"\bmov(?:e|ed|es|ing)\b|\bhow far\b", re.IGNORECASE),
    # Policy 0.3.6: more everyday movement words, about the person's own
    # movement ("how do people get around campus?" is not).
    re.compile(
        r"^(?=.*\b(?:i|i['’]?ve|i['’]?m|im|my|me)\b)"
        r".*(?:\bwalk(?:s|ed|ing)?\b|\b(?:getting|get|got|gotten) around\b"
        r"|\bout and about\b)",
        re.IGNORECASE | re.DOTALL,
    ),
)
_GPS_FEATURE_PATTERNS = _GPS_NAMED_FEATURE_PATTERNS + (
    re.compile(r"\bgps\b", re.IGNORECASE),
    re.compile(r"\blocation\b", re.IGNORECASE),
)

# Policy 0.3.3 (dev Q3/Q4/Q26): naming a feature is enough to be in scope
# (answered from the observed window); no change or time word is needed.
# Bare "gps" and "location" are excluded so place-seeking or off-topic
# questions ("weather at my GPS location") still need evidence intent.
_FEATURE_MENTION_PATTERNS = _UNLOCK_FEATURE_PATTERNS + _GPS_NAMED_FEATURE_PATTERNS


def infer_feature_from_question(question: str) -> str | None:
    """Deterministic keyword match from question text to a `feature_id`.

    Matches only one of the two Tier-1 features
    (`backend.statistics.participant_evidence._FEATURES`: `gps_distance`,
    `unlock_count`) — never inspects participant data, mirrors
    `classify_request`'s text-only contract. A question that matches
    neither feature's keywords, or matches both (genuinely ambiguous), is
    not guessed: return None so the SLM preflight can request a supported
    feature before loading participant data. DEFAULT_FEATURE_ID is retained
    only for older callers that explicitly choose their own default.
    """

    clean_question = question.strip()
    matches_unlock = any(
        pattern.search(clean_question) for pattern in _UNLOCK_FEATURE_PATTERNS
    )
    matches_gps = any(
        pattern.search(clean_question) for pattern in _GPS_FEATURE_PATTERNS
    )

    if matches_unlock and not matches_gps:
        return "unlock_count"
    if matches_gps and not matches_unlock:
        return "gps_distance"

    _logger.warning(
        "feature_inference_ambiguous: question matched %s feature keywords; "
        "no feature selected",
        "both" if (matches_unlock and matches_gps) else "no",
    )
    return None


# There is no user-selected calendar-window contract yet. Even a requested
# fourteen-day period cannot be assumed to match a historical packet's dates.
# Keep unspecified "recent" / "observed window" questions available, but stop
# explicit time requests rather than silently substituting that packet.
_MONTH_NAME = (
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
)
_EXPLICIT_WINDOW_PATTERNS = (
    re.compile(
        r"\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|"
        r"twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|"
        r"twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|"
        r"a|an|a couple of|couple of|few|several)[ -]+"
        r"(?:hours?|days?|weeks?|months?|years?|fortnights?|quarters?|terms?|semesters?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:last|past|previous|next|this)\s+(?:[\w-]+\s+){0,5}"
        r"(?:hours?|days?|weeks?|months?|years?|fortnights?|quarters?|terms?|semesters?)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:today|yesterday|tomorrow|tonight|weekends?)\b", re.IGNORECASE),
    re.compile(r"\b\d{4}-\d{1,2}-\d{1,2}\b|\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b"),
    re.compile(
        r"\b(?:since|from|between|until|through|on|in) (?:the )?(?:\d{1,4}(?:st|nd|rd|th)?|"
        r"monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\b(?:since|from|between|until|through|on|in|during|last|this|next|previous)"
        rf"\s+(?:the\s+)?{_MONTH_NAME}\b",
        re.IGNORECASE,
    ),
    re.compile(rf"\b{_MONTH_NAME}\.?\s+\d{{4}}\b", re.IGNORECASE),
    re.compile(
        r"\b(?:since|from|between|until|through|in|during|last|this|next|previous)"
        r"\s+(?:the\s+)?(?:spring|summer|autumn|fall|winter)\b",
        re.IGNORECASE,
    ),
)


# Policy 0.3.2 (ME-P01 F2, lead decision 2026-10-10): the comparison window
# is the trailing 14 days ([-14, -1], CLAUDE.md), so phrases naming that same
# span refer to the observed window rather than a different calendar range.
# They are removed before the explicit-window check; any other time phrase in
# the question (e.g. "past 3 days", "last month", "yesterday") still refuses.
_OBSERVED_WINDOW_PHRASES = re.compile(
    r"\b(?:the\s+)?(?:past|last|previous)\s+(?:couple(?:\s+of)?|two|2)\s+weeks?\b"
    r"|\b(?:the\s+)?(?:past|last|previous)\s+(?:fortnight|fourteen\s+days|14\s+days)\b",
    re.IGNORECASE,
)

# Policy 0.3.2 (ME-P01 F3): a general question about the evidence's limits
# needs no feature. Without a feature it gets the deterministic uncertainty
# template; with a feature word it still goes to that feature's evidence.
_GENERAL_UNCERTAINTY_PATTERNS = (
    re.compile(r"\bwhat uncertainty should i keep in mind\b", re.IGNORECASE),
    re.compile(
        r"\bwhat (?:are|is) the (?:main )?(?:limitations?|uncertaint(?:y|ies))\b",
        re.IGNORECASE,
    ),
    # Policy 0.3.3 (dev Q14).
    re.compile(
        r"\bhow (?:reliable|accurate|trustworthy|certain) (?:is|are) "
        r"(?:this|that|these|the|your) (?:information|info|answers?|results?|evidence)\b",
        re.IGNORECASE,
    ),
)


def is_general_uncertainty_question(question: str) -> bool:
    """True for a feature-free question about the evidence's limitations."""

    return any(p.search(question) for p in _GENERAL_UNCERTAINTY_PATTERNS) and not (
        any(p.search(question) for p in _UNLOCK_FEATURE_PATTERNS)
        or any(p.search(question) for p in _GPS_FEATURE_PATTERNS)
    )


def request_scope_rejection(
    question: str, *, feature_id: str | None = None, require_feature: bool = False
) -> str | None:
    """Check answer scope after crisis/prohibited routing, without data access.

    A supplied packet or explicit feature can scope a contextual question.
    It cannot override conflicting feature words or an explicit time request.
    Unknown feature IDs remain the API/Statistics owner's validation concern.
    """

    window_text = _OBSERVED_WINDOW_PHRASES.sub(" ", question)
    if any(pattern.search(window_text) for pattern in _EXPLICIT_WINDOW_PATTERNS):
        return "unsupported_time_window"
    matches_unlock = any(
        pattern.search(question) for pattern in _UNLOCK_FEATURE_PATTERNS
    )
    matches_gps = any(pattern.search(question) for pattern in _GPS_FEATURE_PATTERNS)
    if matches_unlock and matches_gps:
        return "ambiguous_feature_request"
    inferred = (
        "unlock_count" if matches_unlock else "gps_distance" if matches_gps else None
    )
    if feature_id in {"gps_distance", "unlock_count"} and inferred not in {
        None,
        feature_id,
    }:
        return "feature_request_mismatch"
    if require_feature and not feature_id and inferred is None:
        return "ambiguous_feature_request"
    return None


def _is_in_scope(question: str) -> bool:
    if any(pattern.search(question) for pattern in _CONTEXTUAL_IN_SCOPE_PATTERNS):
        return True
    if any(pattern.search(question) for pattern in _GENERAL_UNCERTAINTY_PATTERNS):
        return True
    if any(pattern.search(question) for pattern in _FEATURE_MENTION_PATTERNS):
        return True
    return any(pattern.search(question) for pattern in _DOMAIN_PATTERNS) and any(
        pattern.search(question) for pattern in _EVIDENCE_INTENT_PATTERNS
    )


# Policy 0.3.6: informal spellings match like their full forms in every crisis
# family. Applied only to the text used for crisis matching, so the rule
# holds for current and future families without each one listing variants.
# "ill" becomes "i'll" only before a verb or adverb, so "I feel ill" is
# unaffected.
_INFORMAL_SPELLINGS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bwanna\b", re.IGNORECASE), "want to"),
    (re.compile(r"\bgonna\b", re.IGNORECASE), "going to"),
    (re.compile(r"\bgotta\b", re.IGNORECASE), "got to"),
    (re.compile(r"\btryna\b", re.IGNORECASE), "trying to"),
    (re.compile(r"\bdont\b", re.IGNORECASE), "don't"),
    (re.compile(r"\bcant\b", re.IGNORECASE), "can't"),
    (re.compile(r"\bim\b", re.IGNORECASE), "i'm"),
    (re.compile(r"\bive\b", re.IGNORECASE), "i've"),
    # Policy 0.3.7.
    (re.compile(r"\bidk\b", re.IGNORECASE), "i don't know"),
    (re.compile(r"\bdunno\b", re.IGNORECASE), "don't know"),
    (re.compile(r"\bwhats\b", re.IGNORECASE), "what's"),
    (
        re.compile(
            r"\bill\b(?=\s+(?:\w+ly\s+)?(?:be|just|never|not|end|do|kill|hurt|"
            r"take|go|make|try|die|jump|cut|disappear|vanish|leave|stop|finally|"
            r"have|get|give|say|write|sleep|swallow|overdose|miss|see)\b)",
            re.IGNORECASE,
        ),
        "i'll",
    ),
    (re.compile(r"\bu\b", re.IGNORECASE), "you"),
    (re.compile(r"\bur\b", re.IGNORECASE), "your"),
)


def normalise_informal_spelling(text: str) -> str:
    """Rewrite informal spellings to full forms for crisis matching."""

    for pattern, full_form in _INFORMAL_SPELLINGS:
        text = pattern.sub(full_form, text)
    return text


def classify_request(question: str) -> RequestPolicyDecision:
    """Classify one untrusted question without inspecting participant data."""

    clean_question = question.strip()
    crisis_text = normalise_informal_spelling(clean_question)
    if any(pattern.search(crisis_text) for pattern in _CRISIS_PATTERNS):
        return RequestPolicyDecision(
            disposition=RequestDisposition.CRISIS,
            category=RequestCategory.CRISIS_SELF_HARM,
            reason_code="crisis_language_detected",
        )
    # Policy 0.3.7: current emotional distress, with the crisis rules and
    # before diagnosis, so "I feel very depressed" is not a diagnosis refusal.
    if _is_current_distress(crisis_text):
        return RequestPolicyDecision(
            disposition=RequestDisposition.CRISIS,
            category=RequestCategory.CRISIS_SELF_HARM,
            reason_code="current_distress_detected",
        )
    # Policy 0.3.9: asking for help or support, before the privacy rule so a
    # message that also gives an address still gets the crisis template.
    if _is_help_seeking(crisis_text):
        return RequestPolicyDecision(
            disposition=RequestDisposition.CRISIS,
            category=RequestCategory.CRISIS_SELF_HARM,
            reason_code="help_seeking_detected",
        )

    for category, reason_code, patterns in _PROHIBITED_PATTERNS:
        if any(pattern.search(clean_question) for pattern in patterns):
            return RequestPolicyDecision(
                disposition=RequestDisposition.REFUSE,
                category=category,
                reason_code=reason_code,
                support_line=True,
            )

    if _is_named_condition_request(clean_question):
        return RequestPolicyDecision(
            disposition=RequestDisposition.REFUSE,
            category=RequestCategory.DIAGNOSIS_SEEKING,
            reason_code="diagnosis_request_detected",
            support_line=True,
        )

    if any(pattern.search(clean_question) for pattern in _CAPABILITY_PATTERNS):
        return RequestPolicyDecision(
            disposition=RequestDisposition.REFUSE,
            category=RequestCategory.CAPABILITY_QUESTION,
            reason_code="capability_question_detected",
        )

    app_information = app_information_reason(clean_question)
    if app_information:
        return RequestPolicyDecision(
            disposition=RequestDisposition.REFUSE,
            category=RequestCategory.APP_INFORMATION,
            reason_code=app_information,
        )

    if not clean_question or not _is_in_scope(clean_question):
        # Fail closed. A crisis message the rules above miss lands here, so
        # every off-topic refusal carries the support line (policy 0.3.5;
        # 0.3.4 left it off clearly unrelated questions).
        return RequestPolicyDecision(
            disposition=RequestDisposition.REFUSE,
            category=RequestCategory.OFF_TOPIC,
            reason_code="off_topic_request_detected",
            support_line=True,
        )

    return RequestPolicyDecision(
        disposition=RequestDisposition.ALLOW,
        category=RequestCategory.IN_SCOPE,
    )
