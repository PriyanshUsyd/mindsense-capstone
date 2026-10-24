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

REQUEST_POLICY_VERSION = "0.5.0"

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
    # Policy 0.4.0 (practice set v1): wider crisis meaning families.
    # Not being able, or too tired, to keep living.
    re.compile(
        r"\b(?:can['’]?t|cannot|can not|unable to|don['’]?t think i can|do not think "
        r"i can|not sure i can|no longer able to) (?:keep|go on|carry on|continue) "
        r"(?:living|existing|being alive|like this)\b"
        r"|\b(?:tired|sick|exhausted|weary) of (?:living|existing|being alive|life|"
        r"being here|waking up)\b",
        re.IGNORECASE,
    ),
    # Goodbye letters to people, and "it's time" said as the end of a message.
    re.compile(
        r"\b(?:wr(?:ite|ote|itten|iting)|left|leave|leaving|leaves) (?:\w+ ){0,2}"
        r"(?:letters?|notes?) (?:to|for) (?:everyone|everybody|the people i love|"
        r"each of (?:them|you)|them all|my (?:family|mum|mom|dad|parents|sister|"
        r"brother|siblings|partner|friends?|best (?:friend|mate)|mates?|kids|"
        r"children|girlfriend|boyfriend|wife|husband|loved ones))\b"
        r"|\bjust in case\b.{0,40}\b(?:time|goodbye|gone|letters?|notes?)\b"
        r"|\b(?:it )?(?:feels?|seems?) like (?:it['’]?s |it is )?(?:the right |my )?"
        r"time(?: to go)?\s*[.!?]*\s*$",
        re.IGNORECASE | re.DOTALL,
    ),
    # No point in waking up, tomorrow, existing.
    re.compile(
        r"\bpoint (?:of|in) (?:even )?(?:waking up|getting up in the morning|"
        r"tomorrow|existing|being alive|carrying on|it all)\b",
        re.IGNORECASE,
    ),
    # Would anyone notice or care if I were gone; stopping being around.
    re.compile(
        # Noticing or caring about the person being gone, not about a data
        # change ("would anyone notice the drop in my movement?").
        r"\b(?:would|will) (?:anyone|anybody|someone|people) (?:even |actually |"
        r"really |ever )?(?:(?:notice|care)(?: if| when| that)? (?:i|i['’]m|i was|"
        r"i were|i had)\b|care\s*[?.!]*\s*$|miss me|remember me)"
        r"|\bif (?:anyone|anybody) (?:would|will) (?:even |actually |really )?"
        r"(?:(?:notice|care)(?: if| when| that)? (?:i|i['’]m|i was|i were)\b|"
        r"miss me)"
        r"|\b(?:stop|stopped|stopping) (?:being (?:around|here|alive)|existing)\b"
        r"|\b(?:if|when) i (?:was|were|am|['’]m) (?:out of the picture|gone for good|"
        r"no longer around|no longer here|not around any ?more|not here any ?more)\b",
        re.IGNORECASE,
    ),
    # Fear of what one might do to oneself.
    re.compile(
        r"\b(?:scared|afraid|frightened|terrified|worried) (?:of|about) what i "
        r"(?:might|could|will|may|would|['’]ll|am going to|['’]m going to) do\b"
        r"|\b(?:don['’]?t|do not) trust myself\b",
        re.IGNORECASE,
    ),
)

# Policy 0.5.0: reports of personal abuse, violence, threats or coercive
# control route to the deterministic crisis template before any other class.
# These patterns are intentionally first-person and context-bounded so that
# general discussion of violence does not become a personal safety finding.
# Post-practice-v2 (2026-10-24): the family covers any physical or threat verb
# against "me" or a part of the person's body ("grabbed my arm", "slapped my
# face"), being left bruised or marked, and fear of a partner or family
# member. Everyday senses ("hit me up", "grabbed me a coffee", "pushed me to
# walk more", "hit with deadlines") are excluded.
_ABUSE_PERSON = (
    r"(?:someone|somebody|he|she|they|a (?:man|guy|woman|stranger)|"
    r"my (?:partner|ex|ex-partner|boyfriend|bf|girlfriend|gf|husband|wife|"
    r"fianc[eé]e?|spouse|parents?|mum|mom|dad|mother|father|"
    r"step-?(?:mum|mom|dad|mother|father)|brother|sister|family member|carer|"
    r"housemate|flatmate|roommate))"
)
_ABUSE_VERB = (
    r"(?:hurt\w*|hit|hits|hitting|grab\w*|chok\w*|strangl\w*|throttl\w*|"
    r"push\w*|shov\w*|slap\w*|smack\w*|punch\w*|kick\w*|beat|beats|beating|"
    r"beaten|bruis\w*|pinn\w*|restrain\w*|attack\w*|assault\w*|threaten\w*|"
    r"control\w*|abus\w*)"
)
_ABUSE_TARGET = (
    r"(?:me|my (?:arms?|wrists?|neck|throat|face|head|hair|body|legs?|back|"
    r"shoulders?|chest|stomach|hands?|cheek|eyes?|jaw|ribs))"
)
_ABUSE_EVERYDAY_SENSE = (
    r"(?!\s+me\s+(?:up\b|a\b|an\b|some\b|to\s+(?!the\b)\w+|into\s+\w+ing\b))"
)
_ABUSE_VIOLENCE_CRISIS_PATTERNS = (
    re.compile(
        rf"\b{_ABUSE_PERSON}\b.{{0,45}}\b{_ABUSE_VERB}\b{_ABUSE_EVERYDAY_SENSE}"
        rf".{{0,25}}\b{_ABUSE_TARGET}\b",
        re.IGNORECASE | re.DOTALL,
    ),
    # Left bruised or marked by someone.
    re.compile(
        rf"\b{_ABUSE_PERSON}\b.{{0,45}}\b(?:left|leaves|leaving|gave|gives|"
        r"giving)\b(?: me)?(?: with)?(?: a| some)? (?:bruises?|marks?|black eyes?|"
        r"a black eye)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    # Fear of a partner or family member, or of what they will do.
    re.compile(
        r"\b(?:scared|afraid|frightened|terrified|fearful) (?:of|to go home to|"
        r"to be (?:around|near|alone with)|to (?:leave|tell)) "
        r"(?:my (?:partner|ex|ex-partner|boyfriend|bf|girlfriend|gf|husband|wife|"
        r"fianc[eé]e?|spouse|parents?|mum|mom|dad|mother|father|"
        r"step-?(?:mum|mom|dad|mother|father)|carer)\b"
        r"|(?:him|her)\b(?=\s*(?:$|[.!?,;]|when\b|and\b|now\b|lately\b|"
        r"sometimes\b|at home\b)))"
        rf"|\b(?:scared|afraid|frightened|terrified) (?:of )?what {_ABUSE_PERSON} "
        r"(?:might|will|could|would|['’]ll|is going to|['’]s going to) do\b"
        rf"|\b{_ABUSE_PERSON} (?:\w+ ){{0,2}}(?:scares?|scared|frightens?|"
        r"frightened|terrifies|terrified|intimidates?|intimidated) me\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:i do not feel|i don't feel|i dont feel|i no longer feel|"
        r"i am not feeling|i'm not feeling|not feeling|feel|feeling)\s+"
        r"(?:safe|unsafe)\s+(?:at|in)\s+(?:my )?home\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:i am|i'm|i was|i've been|i have been|i got)\s+(?:being )?"
        r"(?:hurt|hit|grabbed|choked|strangled|pushed|shoved|slapped|punched|"
        r"kicked|beaten|bruised|threatened|controlled|abused|assaulted|attacked)\b"
        r"(?!\s+(?:to|into|with|up)\b)",
        re.IGNORECASE,
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
        r"|\b13 ?11 ?14\b"
        # Policy 0.4.0: a number to call, ring or text, in any wording.
        r"|\b(?:phone )?numbers? (?:that )?(?:i|we|someone|you) (?:can|could|should|"
        r"might) (?:call|ring|text|phone)\b"
        r"|\b(?:phone )?numbers? to (?:call|ring|text)\b",
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
    r"\b(?:i|i['’]m|im|i['’]ve|i['’]d|me|my|myself|mine)\b"
    # Policy 0.4.0: "these numbers" and "this data" also refer to the person.
    r"|\b(?:these|those) (?:numbers|results|stats|patterns|readings|figures|scores)\b"
    r"|\bthis (?:data|pattern|result)\b",
    re.IGNORECASE,
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
            # Policy 0.4.0 (practice set v1): the assistant's own setup in any
            # wording. (a) What it was told, or what its prompt, setup,
            # configuration or rules contain, asked about or asked to be
            # shown, listed, pasted or translated.
            re.compile(
                r"\bwhat (?:were|have|was|are) you (?:been )?(?:told|instructed|"
                r"programmed|set up|configured|asked) to\b"
                r"|\bwhat(?:['’]s| is| are| was| were)? (?:in|inside|written in) "
                r"(?:your|the) (?:system |hidden |secret |initial )?(?:prompt|"
                r"instructions|rules|setup|set-up|configuration|config|system message)\b"
                r"|\b(?:show|print|reveal|display|output|repeat|recite|tell me|give me|"
                r"share|list|dump|paste|copy|leak|expose|translate|summari[sz]e|"
                r"read out|spell out|write out)\b.{0,30}\b(?:your|the) (?:\w+ )?"
                r"(?:system message|system prompt|prompt|setup|set-up|setup text|"
                r"configuration|config|initial message|instructions|rules you follow|"
                r"rules you were given|guidelines you follow)\b"
                r"|\b(?:secret|hidden|internal|system) (?:setup|set-up|text|message|"
                r"settings)\b.{0,20}\byou\b"
                r"|\b(?:rules|instructions|guidelines) you (?:follow|run on|use|obey|"
                r"have)\b.{0,30}\b(?:exactly|word for word|verbatim|as written|in full)\b",
                re.IGNORECASE | re.DOTALL,
            ),
            # (b) Persona and role-play framings, and "pretend".
            re.compile(
                r"\b(?:act|behave|respond|answer|reply|talk|speak|write|role-?play)\b"
                r"(?: \w+){0,3} (?:as|like) (?:if )?(?:you (?:were|are|had|have) |"
                r"an? |my |the )?(?:\w+ )?(?:therapist|doctor|psychiatrist|"
                r"psychologist|counsell?or|nurse|gp|unfiltered|uncensored|"
                r"unrestricted|jailbroken|different (?:ai|bot|assistant|model)|ai|"
                r"bot|chatbot|assistant|model|character)\b"
                r"|\b(?:as if|like) you (?:had|have|were|are) (?:no|zero|without)\b"
                r"|\b(?:as if|like) you (?:were|are) (?:a |an |my )?(?:real )?(?:human|"
                r"person|friend|therapist|doctor)\b"
                # "Pretend you're a psychiatrist and diagnose me" stays a
                # diagnosis request (dev Q42), so clinician personas are left out.
                r"|\bpretend (?:that )?"
                r"(?!you(?:['’]re| are| were)? (?:a |an |my )?(?:psychiatrist|"
                r"psychologist|doctor|therapist|counsell?or|nurse|gp|clinician)\b)"
                r"(?:you(?:['’]re| are| were| have| had)?\b|the (?:rules|guidelines|"
                r"restrictions|filters|policy|policies|limits)\b|there (?:are|is|were|"
                r"was) no\b)"
                r"|\bforget (?:that )?you(?:['’]re| are)\b"
                r"|\blet['’]?s (?:role-?play|play a game where you)\b"
                r"|\b(?:from|starting) (?:this point|this moment|now|here) "
                r"(?:on|onwards?|forward)\b.{0,20}\byou\b"
                r"|\b(?:starting|from) (?:right )?now,? you (?:will|are|must|should|can)\b"
                r"|\b(?:ignore|forget|drop|abandon|disregard) (?:all )?(?:your|ur) "
                r"(?:training|programming|setup|safety training)\b",
                re.IGNORECASE | re.DOTALL,
            ),
            # (c) Injected instruction markers and switching safety off.
            re.compile(
                r"</?\s*(?:system|instructions?|admin|developer)\s*>"
                r"|\[(?:system|admin|developer)\]"
                r"|\bnew (?:instructions|rules|system prompt|directives)\s*:"
                r"|\b(?:switch|turn|shut|toggle|take) off (?:your |ur |the |all |any |"
                r"these |those )?(?:own )?(?:safety|content|safe|guard)\w*"
                r"(?: (?:settings?|features?|checks?|mode|filters?|rules|limits))?\b"
                r"|\b(?:ignore|bypass|override|disable|drop|forget) (?:all |the |your |"
                r"ur |any )?(?:mindsense|app['’]?s?|system|model|built-in|usual) "
                r"(?:rules|restrictions|limits|guidelines|filters|policies|policy|"
                r"instructions)\b",
                re.IGNORECASE,
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
            # Policy 0.4.0 (practice set v1): asking which condition the data
            # points to, and something wrong with one's brain, head or mind.
            re.compile(
                r"\b(?:what|which) (?:mental (?:health )?)?(?:conditions?|disorders?|"
                r"illness(?:es)?|diagnos[ei]s|mental illness(?:es)?) (?:do|does|did|"
                r"might|could|would|may|am|is) (?:i|my \w+|these \w+|this \w+|the "
                r"data|my data)\b"
                r"|\b(?:something|anything)(?: is|['’]s)? (?:wrong|off|not right) with "
                r"my (?:brain|head|mind|mental health|psyche)\b"
                r"|\bis my (?:brain|head|mind) (?:broken|wrong|damaged|not (?:right|"
                r"normal|working))\b"
                r"|\b(?:tell me|say|work out|figure out|guess) what (?:i|i['’]ve) "
                r"(?:have|got|am suffering from|suffer from)\b"
                r"|\bwhat (?:do|might|could) i have\s*[?.!]*\s*$",
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
            # Policy 0.4.0 (practice set v1): any named screening scale, and any
            # score, rating, index, grade, level or number for a mental state,
            # in either order.
            re.compile(
                r"\b(?:phq|gad|k[- ]?10|k[- ]?6|kessler|dass(?:[- ]?\d+)?|bdi|beck "
                r"depression|hads|who[- ]?5|epds|edinburgh postnatal)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:depress\w*|anxi\w*|stress|mood|well[- ]?being|wellness|mental "
                r"(?:health|wellness|state)|burn-?out|emotional (?:health|state))\b"
                r"(?: \w+)? (?:score|scores|rating|ratings|index|grade|percentile|"
                r"severity score)\b"
                r"|\b(?:score|scores|scored|rating|grade|number|level|scale|cut-?off|"
                r"threshold|percentile)\b.{0,40}\b(?:how (?:depressed|anxious|"
                r"stressed|sad|low|down|unwell|bad|happy)|my (?:depression|anxiety|"
                r"stress|mood|mental health|well[- ]?being|wellness|burn-?out))\b"
                r"|\b(?:my )?(?:depression|anxiety|stress|mental health)\b.{0,30}\b(?:on "
                r"(?:a|the) (?:\w+ )?scale|scale (?:of|from)|cut-?off|threshold)\b"
                r"|\b(?:rate|grade|score|measure|quantify) (?:how )?(?:depressed|"
                r"anxious|stressed|sad|low|unwell|happy) (?:i am|i['’]m|i['’]ve been|"
                r"i have been|i was)\b",
                re.IGNORECASE | re.DOTALL,
            ),
            re.compile(
                r"\b(?:got|scored|get|getting|had) (?:a |an )?\d+(?:/\d+)? (?:on|in|for) "
                r"(?:a |an |the |my |one of those )?(?:\w+ ){0,2}(?:questionnaire|quiz|"
                r"test|survey|scale|check-?in|assessment|screening|form)\b"
                r"|\b(?:questionnaire|survey|check-?in|screening|assessment) "
                r"(?:scores?|results?|ratings?|totals?)\b",
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
            # Policy 0.4.0 (practice set v1): advice by meaning. What helps or
            # works for a feeling; tips or ways to manage one; needing
            # medication or therapy; the best therapy; whether something is
            # worth trying, would fix or improve a mood, or would make the
            # person happier; making a self-care plan; "should I cut down".
            re.compile(
                r"\bwhat (?:helps|works|would help|could help|can help|might help|"
                r"would work|is good|is best|['’]s good|['’]s best|is helpful)\b"
                r".{0,15}\b(?:with|for|against|on)\b.{0,25}\b(?:anxiety|stress|mood|"
                r"depression|panic|sadness|low mood|overthinking|motivation|sleep|"
                r"insomnia|loneliness|nerves|worry|worrying|feelings?|mental health|"
                r"feeling (?:low|down|sad|anxious|better))\b"
                r"|\b(?:tips|advice|strategies|strategy|techniques?|ways|exercises?|"
                r"tricks|ideas|habits|steps|methods?|hacks)\b.{0,20}\b(?:to|for|on|"
                r"that (?:help|would help|could help))\b.{0,25}\b(?:stop|manage|cope|"
                r"deal with|reduce|beat|overcome|calm|relax|feel|be happier|sleep "
                r"better|overthinking|anxiety|stress|mood|panic|worry|worrying|"
                r"sadness|loneliness)\b"
                r"|\b(?:need|needs|needing) (?:to (?:be on|take|start|see|get) )?"
                r"(?:meds|medication|medicine|antidepressants?|therapy|treatment|"
                r"counsell?ing|a therapist|a psychiatrist|a psychologist)\b"
                r"|\b(?:best|right|good|better|recommended|ideal) (?:kind of |type of |"
                r"form of )?(?:therapy|treatment|medication|medicine|antidepressant|"
                r"supplement|therapist|counsell?or|coping strategy)\b"
                r"|\b(?:worth|a good idea|helpful|beneficial|recommended|effective)\b"
                r".{0,30}\b(?:for|with|against) (?:my )?(?:stress|anxiety|mood|mental "
                r"health|depression|sleep|panic|well[- ]?being|overthinking)\b",
                re.IGNORECASE | re.DOTALL,
            ),
            re.compile(
                r"\b(?:fix|fixes|improve|improves|lift|lifts|boost|boosts|cure|cures|"
                r"treat|treats|ease|eases|sort out|help|helps) (?:with )?(?:my |the |"
                r"this )?(?:mood|anxiety|depression|mental health|stress|"
                r"well[- ]?being|motivation|overthinking|panic(?: attacks)?|sadness|"
                r"low mood|feelings|nerves)\b"
                r"|\b(?:make|help|get) me (?:feel |be |a )?(?:happier|calmer|"
                r"better|less (?:anxious|stressed|sad|down|low|lonely|tired)|more "
                r"(?:relaxed|motivated|positive|energetic|confident))\b"
                r"|\b(?:put together|come up with|build|draft|plan|map out|work out|"
                r"set up|write) (?:me )?(?:a |an |some |my )?(?:personal(?:ised|ized)? )?"
                r"(?:self[- ]care|coping|wellness|well[- ]?being|treatment|recovery|"
                r"mental[- ]health|care|mood) (?:plan|routine|strategy|programme|"
                r"program|regime)\b"
                r"|\bshould i (?:cut down|cut back|cut out|give up|avoid|limit|drink|"
                r"eat|exercise|meditate|journal|work out|go to bed|sleep)\b",
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
            # Policy 0.4.0 (practice set v1): forecasts in more wordings.
            # Heading for an outcome; chances, likelihood or danger of
            # something; what lies ahead; "if this continues"; one's future;
            # ending up worse; what something will look like.
            re.compile(
                r"\b(?:heading|headed|on track|on course|set|bound|destined) (?:for|"
                r"towards?|to) (?:a |an )?(?:breakdown|burn-?out|crash|relapse|crisis|"
                r"collapse|failure|fail|disaster|meltdown|trouble|worse|depression|"
                r"getting worse)\b"
                r"|\b(?:chances?|odds|probability|likelihood|danger|risk)\b (?:is |are )?"
                r"(?:that )?(?:i|i['’]ll|i['’]d|i['’]m|me|my(?! (?:data|information|"
                r"info|privacy|answers?|chats?|messages?)\b))\b"
                r"|\b(?:expect|anticipate|brace (?:myself )?for|prepare (?:myself )?for|"
                r"in for)\b.{0,40}\b(?:ahead|coming|to come|later|worse|harder|rough|"
                r"tough|bad|difficult|hard)\b"
                r"|\b(?:days?|weeks?|months?|years?|term|semester|times?) ahead\b"
                r"|\bif (?:this|it|that|things|my \w+) (?:continues?|keeps? (?:up|going|"
                r"happening)|carr(?:y|ies) on|goes on|stays (?:like this|the same)|"
                r"doesn['’]?t (?:change|stop|improve))\b"
                r"|\bmy future\b.{0,30}\b(?:look\w*|be|seem\w*|hold\w*|bleak|bad|good|"
                r"ok|okay|going)\b|\bfuture (?:looks?|looking|seems?)\b"
                r"|\bend up\b.{0,30}\b(?:worse|depressed|anxious|burnt out|burned out|"
                r"failing|dropping out|needing|in hospital|unwell|sick|alone)\b"
                r"|\bwhat (?:will|would|is going to|['’]s going to|is gonna) (?:my|the|"
                r"things|life|it|this)\b.{0,30}\b(?:look|be|end up|feel) like\b",
                re.IGNORECASE | re.DOTALL,
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
            # Policy 0.4.0 (practice set v1): any causal verb about the
            # person's change (caused, driving, affect, responsible for,
            # stopping me, making me + a verb, explain why). Questions about
            # the baseline, the comparison, the evidence or missing data are
            # app questions, not causal.
            re.compile(
                r"^(?!.*\b(?:baseline|compar\w*|evidence|missing (?:days|data)|"
                r"data quality|uncertain\w*)\b)"
                r".*\b(?:caused|causing|causes|drives|driving|drove|driven|"
                r"affect(?:s|ed|ing)?|impact(?:s|ed|ing)?|influenc(?:e|es|ed|ing)|"
                r"responsible for|to blame|account(?:s|ed)? for|contribut(?:e|es|ed|"
                r"ing) to|explain(?:s|ed)? (?:why|the (?:drop|change|rise|increase|"
                r"decrease|dip|fall|difference))|creat(?:e|es|ed|ing)|produc(?:e|es|ed|ing)|"
                r"(?:stopping|stopped|stops|keeping|"
                r"kept|keeps|making|made|makes) me (?:from )?"
                # Only a behaviour or feeling ("making me move less"), not a
                # request someone made ("made me promise").
                r"(?:feel\w*|be|get\w*|go(?:es|ing)?|stay\w*|leav\w*|use|using|"
                r"check\w*|unlock\w*|pick\w*|mov\w*|travel\w*|walk\w*|sleep\w*|"
                r"scroll\w*|withdraw\w*|isolat\w*|avoid\w*|less|more|so|restless|"
                r"anxious|tired|lazy|sad|low|down|stressed|worse|lonely))\b",
                re.IGNORECASE | re.DOTALL,
            ),
            # Post-practice-v2 (2026-10-24): an explaining or originating verb
            # ("explain", "be behind", "bring about", "trigger", "led to")
            # that links a behaviour to a feeling or wellbeing, in either
            # order ("is my mood explained by ..."). A feeling word is
            # required, so "explain my GPS distance" keeps its evidence route.
            re.compile(
                r"^(?!.*\b(?:baseline|compar\w*|evidence|missing (?:days|data)|"
                r"data quality|uncertain\w*)\b)"
                r"(?=.*\b(?:mood|moods|feel\w*|wellbeing|well-being|sad\w*|distress\w*|"
                r"depress\w*|anxi\w*|stress\w*|emotion\w*|mental (?:health|state)|"
                r"lonel\w*|unhapp\w*|happ(?:y|ier|iness)|upset|struggl\w*|"
                r"exhaust\w*|tired\w*)\b)"
                r".*\b(?:explain(?:s|ed|ing)?|(?:be|is|are|was|were|been) behind|"
                r"br(?:ing|ings|inging|ought) (?:about|on)|g(?:ive|ives|ave|iving) "
                r"rise to|trigger(?:s|ed|ing)?|led to|leads? to|leading to)\b",
                re.IGNORECASE | re.DOTALL,
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
            # Post-practice-v2 (2026-10-24): another account, profile or
            # device, and a specific, named or particular person.
            re.compile(
                r"\b(?:another|other|different) (?:participant|person|user|student|"
                r"individual|account|profile|login|device|phone)s?\b"
                r"|\bindividual(?:['’]s|s)?\b"
                r"|\bother people\b|\b(?:someone|somebody|everyone|anyone) else\b"
                r"|\b(?:a |one |that |this )?(?:specific|particular|certain|named|"
                r"given|real|identifiable) (?:person|people|participant|user|"
                r"student|individual|someone)(?:['’]s|s)?\b",
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
            # Policy 0.4.0 (practice set v1). (a) Raw location data in any
            # phrasing: asking to see, get or export location detail, or naming
            # point-level location data at all. Only distance travelled is
            # described; "what does my location data say about how far I go?"
            # names no raw detail and keeps its evidence route.
            re.compile(
                # Deleting the data is a storage question (app_info_data_storage).
                r"^(?!.*\b(?:delete|remove|erase|wipe|destroy|purge|get rid of)\b)"
                r".*(?:"
                r"\b(?:show|see|view|export|download|send|give|get|access|share|pull|"
                r"list|dump|copy|open|display|print|email|extract|hand over|expose|"
                r"reveal|leak|disclose)\b.{0,30}"
                r"\b(?:(?:raw|exact|precise|full|detailed|all|underlying|actual|"
                r"individual) (?:gps|location|position|geo-?location|movement) "
                r"(?:data|readings?|records?|details?|info(?:rmation)?|locations?|"
                r"positions?|places|whereabouts)"
                r"|(?:gps|location|position|geo-?location) (?:history|log|logs|points?|"
                r"pings?|coordinates|co-ordinates|trail|trace|tracks?|file|export|"
                r"fixes|records?))\b"
                r"|\b(?:latitudes?|longitudes?|lat ?/ ?long|lat-?long|lat/lng|"
                r"co-?ordinates|geo-?coordinates)\b"
                r"|\b(?:gps|location) (?:pings?|points?|trail|trace|logs?|fixes|"
                r"coordinates|co-ordinates)\b|\blocation (?:history|trail)\b"
                r"|\braw (?:gps|location|movement|sensor) (?:data|logs?|files?|"
                r"readings|points)\b"
                r"|\b(?:map|list|record|log|timeline) of (?:where|the places|places|"
                r"everywhere|locations|my locations)\b"
                r"|\b(?:csv|spreadsheet|file|export|download|copy) of (?:my |all my |"
                r"all of my )?(?:location|gps|movement)\b)",
                re.IGNORECASE | re.DOTALL,
            ),
            # (b) Places the person went: where they were or go, which places,
            # venues or suburbs they visit, where they spend most time.
            re.compile(
                r"\bwhere (?:exactly |else |abouts |precisely )?(?:was|were|did|have|"
                r"had|do|does) i (?:usually |normally |"
                r"often |mostly |last )?(?:been|go|gone|went|spend|hang|on|at|tend to|"
                r"end(?:ed)? up|head(?:ed)?|wander(?:ed)?)\b"
                r"|\bwhere i(?:['’]ve| have)? (?:been|go|went|gone|spend|spent|hang "
                r"out)\b"
                r"|\b(?:which|what) (?:places?|locations?|caf[eé]s?|shops?|stores?|"
                r"bars?|pubs?|restaurants?|venues?|spots?|suburbs?|neighbou?rhoods?|"
                r"buildings?|streets?|parts of (?:town|the city|campus)|gyms?|clubs?) "
                r"(?:did|do|have|had|was|were) i\b"
                r"|\b(?:places|locations|spots|venues) (?:that )?i (?:visit\w*|go|went|"
                r"frequent\w*|have been|spend)\b"
                r"|\b(?:spend|spent|spending) (?:the )?most (?:of my )?time (?:at|in)\b",
                re.IGNORECASE,
            ),
            # (c) Other people's data and identities, and study identifiers.
            re.compile(
                r"\b(?:is|are|was|were|has|have|does|do|did) (?:my|her|his|their|our) "
                r"(?:roommate|room-mate|flatmate|flat-mate|housemate|partner|"
                r"boyfriend|girlfriend|ex|husband|wife|friends?|best friend|sister|"
                r"brother|sibling|mum|mom|dad|mother|father|parents?|classmates?|"
                r"family|colleagues?|co-?workers?|neighbou?rs?|kids?|son|daughter|"
                r"child)\b (?:\w+ ){0,2}(?:unlock\w*|mov\w*|travel\w*|go(?:es|ing)?|"
                r"went|been|using|walk\w*|location|data|whereabouts)\b"
                r"|\b(?:than|to|with|vs\.?|versus|against) (?:my|her|his|their|our) "
                r"(?:roommate|room-mate|flatmate|flat-mate|housemate|partner|"
                r"boyfriend|girlfriend|ex|husband|wife|friends?|best friend|sister|"
                r"brother|sibling|mum|mom|dad|mother|father|parents?|classmates?|"
                r"colleagues?|co-?workers?|neighbou?rs?)(?:['’]s?)?\b"
                r"|\bwhere(?:['’]s| is| has| have| did| does)? (?:my|her|his|their|our) "
                r"(?:roommate|flatmate|housemate|"
                r"partner|boyfriend|girlfriend|ex|husband|wife|friends?|sister|"
                r"brother|mum|mom|dad|parents?|classmates?|colleagues?|neighbou?rs?|"
                r"kids?|son|daughter)\b"
                r"|\b(?:names?|identit(?:y|ies)|ids?|identifiers?|contact details) of "
                r"(?:the |any |other |another |a )?(?:participants?|people|persons?|"
                r"students?|users?|subjects?)\b"
                r"|\bwho else\b.{0,25}\b(?:study|app|mindsense|data|using|"
                r"participat\w*|in this)\b"
                r"|\b(?:my|the|our|a) (?:participant|study|subject|user|research) "
                r"(?:id|ids|number|identifier|code|uid)\b",
                re.IGNORECASE | re.DOTALL,
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
    # Policy 0.4.0 (practice set v1): what the assistant is, what it can or
    # cannot do and what to ask, in more wordings. Not anchored, but every
    # branch names the assistant or its abilities, so evidence questions
    # ("what can you tell me about my unlocks?") are not captured. Asking to
    # talk about feelings is left to the support-line refusal on purpose.
    re.compile(
        r"\bwhat (?:can|could|should|may) i ask(?: you)?(?: about)?\s*[?.!]*\s*$"
        r"|\bwhat (?:are|r) (?:you|u) (?:able to|capable of|good for|for)\b"
        r"|\bwhat (?:exactly )?(?:do|can|could) (?:you|u) (?:actually |really |even |"
        r"exactly )?(?:do|help (?:me )?with|"
        r"offer)\b(?!\s+(?:with|to|about) (?:my|the)\b)"
        r"|\bwhat(?:['’]s| is) (?:this|the|mindsense|this thing) (?:app |tool |thing |"
        r"chatbot |bot |assistant )?(?:for|about)\s*[?.!]*\s*$"
        r"|\bwhat(?:['’]s| is| are) (?:your|its) (?:main )?(?:purpose|point|features?|"
        r"capabilities|abilities|functions?|job|role)\b"
        r"|\bwhat (?:can['’]?t|cannot|can not) (?:you|u|mindsense|it) do\b"
        r"|\bwhat (?:can|could|does|will|would) (?:this|the|mindsense) ?(?:app|tool|"
        r"thing|chatbot|bot|assistant)? do(?: for me)?\b"
        r"|\b(?:are|r) (?:you|u) (?:a |an )?(?:real |actual |licensed |qualified |"
        r"proper |trained )?(?:therapist|doctor|counsell?or|psychologist|"
        r"psychiatrist|human|person|bot|chatbot|robot|ai|machine|computer)\b"
        r"|\bis (?:this|it|mindsense) (?:a |an )?(?:chatbot|bot|real person|person|"
        r"human|ai|robot|therapist)\b"
        r"|\b(?:are|r) (?:you|u) (?:like|similar to|the same as) (?:siri|alexa|"
        r"chat ?gpt|google|gemini|copilot|a chatbot)\b"
        r"|\b(?:explain|tell me|describe|show me) what (?:you|u|mindsense|this app)"
        r"(?:['’]re| are| can| is)? (?:capable of|able to do|can do|for|does)\b"
        r"|\b(?:example|sample) questions\b"
        r"|\bwhat (?:kinds?|sorts?|types?) of (?:questions|things|stuff)\b"
        r"|\bcan (?:you|u) only (?:talk|answer|help|do)\b"
        r"|\bdo (?:you|u) do anything (?:besides|else|other than|apart from|except)\b"
        r"|\bwhat(?:['’]s| is) possible (?:here|with (?:you|this app|mindsense))\b",
        re.IGNORECASE,
    ),
    # Questions about the assistant's access or actions are capabilities even
    # when the object contains an in-scope feature word. Comparison verbs are
    # intentionally excluded so evidence questions remain in scope.
    re.compile(
        r"\b(?:can|could|do|does|are|is) (?:you|the app|this app|mindsense|"
        r"the assistant|the chatbot)\b.{0,50}\b(?:access|read|monitor|record|"
        r"contact|book|remember|change|listen|use the camera|use the microphone)\b",
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
    # Policy 0.4.0 (practice set v1): the same app questions in more wordings.
    (
        "app_info_sensors",
        re.compile(
            r"\b(?:know|knows|see|sees|watch\w*|track\w*|follow\w*|record\w*)\b.{0,25}"
            r"\b(?:my location|where i am|where i go|my whereabouts|my position)\b"
            r".{0,25}\b(?:all the time|always|constantly|24/7|at all times|every "
            r"minute|in the background|right now|live|in real time)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "app_info_data_use",
        re.compile(
            r"\b(?:what|which) (?:kinds?|sorts?|types?) of (?:data|information|info|"
            r"sensors?|measures?) (?:do|does|did|will|can) (?:you|mindsense|the app|"
            r"this app|it)\b"
            r"|\b(?:what|which) (?:sensors?|data|information|measures|signals|"
            r"inputs) (?:do|does|did) (?:you|mindsense|the app|this app|it) (?:use|"
            r"collect|look at|need|rely on|read|track|draw on|have|record|capture)\b"
            r"|\bhow (?:far back|long|many (?:days|weeks|months)(?: back)?) (?:does|do) "
            r"(?:your|the|its|my|this app['’]?s|mindsense['’]?s) (?:data|history|"
            r"records?|information)(?: \w+)? (?:go|cover|span|stretch|last)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "app_info_data_storage",
        re.compile(
            r"\b(?:sent|send|sending|uploaded|upload\w*|go(?:es)?|going|shared|"
            r"stored|saved|kept|backed up|synced)\b.{0,15}\b(?:to|on|in|onto|with) "
            r"(?:the |a |an |any |some )?(?:cloud|internet|server|servers|online|web|openai|google|"
            r"third parties)\b"
            r"|\bwho (?:can|could|will|gets to|is able to) (?:see|read|access|view|"
            r"look at)\b"
            r"|\b(?:can|could|will|would|does|do) (?:my )?(?:lecturer|tutor|uni|"
            r"university|teacher|professor|parents?|family|employer|researchers?|"
            r"staff|the (?:study|research) team|the government|police) (?:see|access|"
            r"read|view|look at|find out|get)\b"
            r"|\b(?:delete|remove|erase|wipe|destroy|purge|get rid of) (?:everything|"
            r"all|anything|whatever|all the (?:data|info|information)) (?:you(?: have|"
            r"['’]ve got| hold| store| keep| know)? )?(?:on|about|of) me\b"
            r"|\b(?:model|ai|llm|chat ?gpt|openai|language model|a human|a person|"
            r"someone|anyone|people)\b.{0,15}\b(?:read(?:ing|s)?|see(?:ing|s)?|"
            r"look(?:ing|s)? at|process\w*|stor\w*|log\w*)\b.{0,10}\b(?:my )?"
            r"(?:messages|chats?|questions|conversations?|what i (?:type|write|ask|"
            r"say))\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "app_info_uncertain_evidence",
        re.compile(
            r"^(?=.*\bmean(?:s|ing|t)?\b)"
            r"(?=.*(?:no clear difference|uncertain|not (?:clearly )?different|"
            r"evidence is (?:weak|not strong)|not reportable)).*",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "app_info_baseline_unavailable",
        re.compile(
            r"\bwhy (?:is(?:n['’]?t| there no| there not)|are(?:n['’]?t| there no)|"
            r"can['’]?t|cannot|won['’]?t|don['’]?t|didn['’]?t|no)\b.{0,30}"
            r"\b(?:comparison|compar\w*|baseline|my usual|my normal)\b",
            re.IGNORECASE | re.DOTALL,
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
    # Policy 0.4.0 (practice set v1): a general question about the person's
    # own tracked data, patterns, routine or habits with a change, comparison
    # or summary cue. It names no single feature, so preflight asks
    # "movement or phone unlocks?"; with a feature word it is answered.
    re.compile(
        r"^(?=.*\b(?:my|me|i)\b)"
        # Untracked measures keep the off-topic refusal.
        r"(?!.*\b(?:sleep\w*|steps?|heart|calories|water|music|spotify|instagram|"
        r"tiktok|weight|diet|food|eating|exercise|workouts?|gym|grades?|marks|"
        r"assignments?|homework|bank|money|spending|budget|period|cycle)\b)"
        r"(?=.*\b(?:data|patterns?|numbers|stats|readings|measures|metrics|figures|"
        r"results|tracked \w+|activity|activities|routine|habits|behaviou?r)\b)"
        r"(?=.*\b(?:chang\w*|different\w*|differ\w*|shift\w*|normal|usual|unusual|"
        r"typical|overview|summar\w*|look\w*|check|show\w*|stand\w* out|trend\w*|"
        r"compar\w*|going on|doing|tell me about|describe|explain|recap|update on|"
        r"how (?:is|are|was|were))\b)",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\b(?:anything|something) (?:unusual|different|odd|new|weird|strange|"
        r"notable|interesting) (?:with|about|in|for) (?:me|my)\b"
        r"|\b(?:am i|have i been|i['’]?m|i am) (?:behaving|acting|living) (?:any )?"
        r"differently\b"
        r"|\bhow (?:have|has) i been (?:doing|going|getting on)\b|\bhow['’]?ve i been\b"
        r"|\bhow active and\b|\bhow (?:connected|social|busy) (?:have|had|was|am) i\b"
        r"|\b(?:which|what) of my (?:two |2 )?(?:measures|features|metrics|numbers|"
        r"stats|patterns)\b",
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
    # Policy 0.4.0: checking, opening, grabbing or picking up the phone.
    re.compile(
        r"\b(?:check|checks|checking|checked|open|opens|opening|opened|grab|grabs|"
        r"grabbing|grabbed|look at|looking at|looked at|reach for|reaching for|"
        r"reached for)\b (?:my |the )?phone\b"
        r"|\bphone (?:checking|checks|pickups?|opens)\b"
        r"|\bpick(?:s|ed|ing)? (?:my |the )?phone up\b",
        re.IGNORECASE,
    ),
)

_GPS_NAMED_FEATURE_PATTERNS = (
    re.compile(r"\btravel(?:l?ed|ling|s)?\b", re.IGNORECASE),
    re.compile(r"\bdistance\b", re.IGNORECASE),
    re.compile(r"\bmovement\b", re.IGNORECASE),
    re.compile(r"\bmobility\b", re.IGNORECASE),
    # Policy 0.3.3 (dev Q1/Q15): everyday wording for distance moved.
    # Policy 0.4.0: "how far" now needs the person ("how far did I go?");
    # "how far is Perth from Darwin?" is not a movement question. See below.
    re.compile(r"\bmov(?:e|ed|es|ing)\b", re.IGNORECASE),
    # Policy 0.3.6: more everyday movement words, about the person's own
    # movement ("how do people get around campus?" is not).
    re.compile(
        r"^(?=.*\b(?:i|i['’]?ve|i['’]?m|im|my|me)\b)"
        r".*(?:\bwalk(?:s|ed|ing)?\b|\b(?:getting|get|got|gotten) around\b"
        r"|\bout and about\b)",
        re.IGNORECASE | re.DOTALL,
    ),
    # Policy 0.4.0: "how far", "how mobile", kilometres, ground covered, about
    # the person's own movement ("how many km from Sydney to Melbourne?" is not).
    re.compile(
        r"^(?=.*\b(?:i|i['’]?ve|i['’]?m|im|my|me)\b)"
        r".*(?:\bhow far\b|\b(?:km|kms|kilomet(?:re|er)s?|miles)\b"
        r"|\bmobile\b(?! (?:phone|app|number|data|plan)\b)"
        r"|\bground\b.{0,20}\bcover\w*|\bcover\w*\b.{0,20}\b(?:ground|distance|"
        r"kilomet\w*|km|kms|miles)\b|\b(?:kilomet\w*|km|kms|miles)\b.{0,20}\b(?:i|"
        r"i['’]?ve|i have)\b.{0,10}\b(?:covered|done|walked|travel\w*|moved)\b)",
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

# Policy 0.4.0: common misspellings of the feature words ("mvoement",
# "unlcoks", "movemnt"). A word of five or more letters counts as a feature
# word when it differs from one by two swapped neighbouring letters or one
# missing letter. An added letter is not accepted, so "unblock" never becomes
# "unlock". Used only to find the feature, never for crisis or refusal rules.
_FEATURE_WORDS = (
    "movement", "movements", "mobility", "distance", "travelled", "traveled",
    "travelling", "traveling", "unlock", "unlocks", "unlocked", "unlocking",
)
_WORD = re.compile(r"[A-Za-z]{5,}")


def _is_feature_typo(word: str, target: str) -> bool:
    if word == target:
        return False
    if len(word) == len(target):
        diffs = [i for i, (a, b) in enumerate(zip(word, target)) if a != b]
        return (
            len(diffs) == 2
            and diffs[1] == diffs[0] + 1
            and word[diffs[0]] == target[diffs[1]]
            and word[diffs[1]] == target[diffs[0]]
        )
    if len(word) == len(target) - 1:
        return any(target[:i] + target[i + 1 :] == word for i in range(len(target)))
    return False


def _normalise_feature_typos(text: str) -> str:
    def fix(match: re.Match[str]) -> str:
        word = match.group(0)
        lower = word.lower()
        if lower in _FEATURE_WORDS:
            return word
        for target in _FEATURE_WORDS:
            if _is_feature_typo(lower, target):
                return target
        return word

    return _WORD.sub(fix, text)


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

    clean_question = _normalise_feature_typos(question.strip())
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
        r"\b(?:last|past|previous|prior|next|this)\s+(?:[\w-]+\s+){0,5}"
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
    # Policy 0.4.0 (practice set v1): more named periods.
    # Parts of a day ("this morning", "Friday night").
    re.compile(
        r"\b(?:this|last|yesterday|tomorrow|sunday|monday|tuesday|wednesday|"
        r"thursday|friday|saturday) (?:morning|afternoon|evening|night|arvo|"
        r"lunchtime)\b",
        re.IGNORECASE,
    ),
    # A month with a day, or early / mid / late / "of" a month.
    re.compile(
        rf"\b(?:of|early|mid|late|end of|start of|beginning of|middle of)[ -]+"
        rf"{_MONTH_NAME}\b"
        rf"|\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:of\s+)?{_MONTH_NAME}\b"
        rf"|\b{_MONTH_NAME}\s+\d{{1,2}}(?:st|nd|rd|th)?\b",
        re.IGNORECASE,
    ),
    # The start, end or first week of a period; named breaks, holidays,
    # exam periods and weeks of the academic year.
    re.compile(
        r"\b(?:since|from|during|over|across|in|through(?:out)?|before|after|"
        r"around|until|till)\s+(?:the\s+)?(?:start|beginning|end|middle) of\b"
        r"|\b(?:first|second|third|last|final) (?:week|weekend|day|fortnight|month) "
        r"(?:of|in)\b"
        r"|\b(?:easter|christmas|xmas|new year['’]?s?|mid-?(?:semester|sem|year|"
        r"term)|winter|summer|spring|autumn|uni|university|exam|exams|school|"
        r"holiday|semester|term|o-?week|orientation|study|stuvac|reading|teaching) "
        r"(?:break|holidays?|period|week|weeks|season|vacation|vac)\b"
        r"|\b(?:over|during|across|in|since|before|after) (?:the )?(?:holidays|"
        r"break|exams|exam period|vacation|hols)\b",
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

# Policy 0.4.0: a rate ("times a day", "unlocks per week") describes how often,
# not a period, so it is removed before the explicit-window check.
_RATE_PHRASES = re.compile(
    r"\b(?:times|unlocks?|pick-?ups?|km|kms|kilomet(?:re|er)s|miles|metres|"
    r"meters)\s+(?:a|an|per|each|every)\s+(?:day|week|night)\b",
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

    feature_text = _normalise_feature_typos(question)
    return any(p.search(question) for p in _GENERAL_UNCERTAINTY_PATTERNS) and not (
        any(p.search(feature_text) for p in _UNLOCK_FEATURE_PATTERNS)
        or any(p.search(feature_text) for p in _GPS_FEATURE_PATTERNS)
    )


def request_scope_rejection(
    question: str, *, feature_id: str | None = None, require_feature: bool = False
) -> str | None:
    """Check answer scope after crisis/prohibited routing, without data access.

    A supplied packet or explicit feature can scope a contextual question.
    It cannot override conflicting feature words or an explicit time request.
    Unknown feature IDs remain the API/Statistics owner's validation concern.
    """

    window_text = _RATE_PHRASES.sub(" ", _OBSERVED_WINDOW_PHRASES.sub(" ", question))
    if any(pattern.search(window_text) for pattern in _EXPLICIT_WINDOW_PATTERNS):
        return "unsupported_time_window"
    feature_text = _normalise_feature_typos(question)
    matches_unlock = any(
        pattern.search(feature_text) for pattern in _UNLOCK_FEATURE_PATTERNS
    )
    matches_gps = any(
        pattern.search(feature_text) for pattern in _GPS_FEATURE_PATTERNS
    )
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
    question = _normalise_feature_typos(question)
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


_UNTRACKED_MEASURE_PATTERNS = (
    re.compile(
        r"\b(?:sleep(?:ing)? duration|sleep quality|heart rate|"
        r"calories|calorie intake|water intake|body weight|workouts?|"
        r"exercise sessions?|screen[- ]time duration)\b",
        re.IGNORECASE,
    ),
)


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
    if any(
        pattern.search(crisis_text) for pattern in _ABUSE_VIOLENCE_CRISIS_PATTERNS
    ):
        return RequestPolicyDecision(
            disposition=RequestDisposition.CRISIS,
            category=RequestCategory.CRISIS_SELF_HARM,
            reason_code="abuse_violence_safety_detected",
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

    app_information = app_information_reason(clean_question)
    if app_information:
        return RequestPolicyDecision(
            disposition=RequestDisposition.REFUSE,
            category=RequestCategory.APP_INFORMATION,
            reason_code=app_information,
        )


    if any(pattern.search(clean_question) for pattern in _CAPABILITY_PATTERNS):
        return RequestPolicyDecision(
            disposition=RequestDisposition.REFUSE,
            category=RequestCategory.CAPABILITY_QUESTION,
            reason_code="capability_question_detected",
        )

    if any(pattern.search(clean_question) for pattern in _UNTRACKED_MEASURE_PATTERNS):
        return RequestPolicyDecision(
            disposition=RequestDisposition.REFUSE,
            category=RequestCategory.OFF_TOPIC,
            reason_code="untracked_measure_request",
            support_line=True,
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
