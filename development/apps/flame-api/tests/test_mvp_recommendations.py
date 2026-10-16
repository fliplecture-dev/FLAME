"""Representative, rollback-only recommendation journeys; no real student data/provider calls."""
from io import BytesIO
from tempfile import TemporaryDirectory
from uuid import UUID, uuid4
from PIL import Image
from app.modules.functional.identity.dependencies import require_admin, require_member
from app.modules.functional.conversations.models import ConversationSession, Message
from app.modules.decision_engine.recommendation.learning_need import split_intent
from app.modules.decision_engine.recommendation.selection import learning_need, select_recommendations
from app.modules.application.teaching.gateway import Generated
from test_curriculum_workspace import isolated_client


def test_intent_metadata_fallback_and_untrusted_concepts():
    text, need = split_intent('Gravity pulls. <flame-intent>{"intent":"demonstrate","concept":"gravity","language":"en"}</flame-intent>')
    assert text == 'Gravity pulls.' and need['intent'] == 'demonstrate'
    assert split_intent('Gravity pulls. <flame-intent>broken')[0] == 'Gravity pulls.'
    assert learning_need('explain gravity', '', {'intent':'explain','concept':'plants','language':'en'})['source'] == 'fallback'
    assert learning_need('explain gravity', '', {'intent':'human_help','concept':'gravity','language':'en'})['intent'] == 'explain'
    assert learning_need('test my understanding', 'explain gravity')['intent'] == 'practise'
    assert learning_need('show how it works', 'explain gravity')['intent'] == 'demonstrate'
    assert select_recommendations([], learning_need('explain gravity',''), 'explain gravity','Gravity pulls.')['display_mode'] == 'none'
    # Preferences are not hard media-type bans: a relevant video can explain when no illustration exists.
    video={'id':'video','kind':'resource','type':'video','version':1,'title':'Gravity','description':'Gravity pulls objects down.','availability_state':'available'}
    assert select_recommendations([video],learning_need('explain gravity',''),'explain gravity','Gravity pulls.')['primary']['candidate_id']=='video'


def test_mvp_owned_selection_history_kits_tutors_and_rechecks(monkeypatch):
    with isolated_client() as client, TemporaryDirectory() as directory:
        config = client.app.state.settings
        config.resource_allowed_hosts='media.example.test';config.resource_local_dir=directory
        c=client.post('/api/v1/admin/curricula',json={'code':'mvp-'+uuid4().hex[:8],'name':'MVP fixture'}).json();cid=c['id']
        def child(kind,parent,name):
            r=client.post('/api/v1/admin/curriculum/'+kind,json={'parent_id':parent,'name':name});assert r.status_code==201,r.text;return r.json()['id']
        level=child('level',cid,'Grade 1');subject=child('subject',level,'Science');domain=child('domain',subject,'Motion')
        topic=child('topic',domain,'Force and Gravity');leaf=child('subtopic',topic,'Chapter 1')
        tree=client.get('/api/v1/admin/curricula/'+cid+'/tree').json()
        pub=client.post('/api/v1/admin/curriculum/curriculum/'+cid+'/publish',json={'expected_version':tree['version'],'expected_draft_revision':tree['draft_revision']});assert pub.status_code==200,pub.text;revision=pub.json()['revision']
        def media(title,kind='image',published=True):
            r=client.post('/api/v1/admin/resources',json={'title':title,'description':title+' Grade 1 lesson','type':kind,
                'external_url':'https://media.example.test/'+uuid4().hex+'.png','alt_text':title,'caption_or_transcript':title,
                'rights_basis':'owned','rights_holder':'Fixture','distribution_scope':'members','paths':[{'topic_id':topic,'subtopic_id':leaf}]});assert r.status_code==201,r.text
            row=r.json()
            if published:
                r=client.post('/api/v1/admin/resources/'+row['id']+'/publish',json={'expected_version':row['version']});assert r.status_code==200,r.text;row=r.json()
            return row
        force=media('Force push pull');gravity=media('Gravity falling ball');video=media('Gravity falling ball demonstration','video')
        media('Plant leaves');media('Gravity unpublished',published=False)
        advanced=media('Gravity Grade 9 equations')
        # Explicit higher-grade metadata excludes it despite mapping and Grade 1 in description.
        r=client.patch('/api/v1/admin/resources/'+advanced['id'],json={'expected_version':advanced['version'],'description':'Grade 9 gravity equations'});assert r.status_code==200,r.text
        teacher=client.post('/api/v1/admin/teachers',json={'name':'Motion tutor','bio':'Force and gravity','languages':['English'],'expertise':[{'subject_id':subject,'topic_id':topic}]}).json()
        r=client.post('/api/v1/admin/teachers/'+teacher['id']+'/publish',json={'expected_version':teacher['version']});assert r.status_code==200,r.text;teacher=r.json()
        offline=client.post('/api/v1/admin/teachers',json={'name':'Offline tutor','availability':'Unavailable','expertise':[{'subject_id':subject}]}).json()
        assert client.post('/api/v1/admin/teachers/'+offline['id']+'/publish',json={'expected_version':offline['version']}).status_code==200
        data=BytesIO();Image.new('RGB',(3,3),'blue').save(data,'PNG')
        upload=client.post('/api/v1/admin/resources/uploads',files={'file':('kit.png',data.getvalue(),'image/png')}).json()
        kit=client.post('/api/v1/admin/activity-kits',json={'name':'Gravity falling ball practice','description':'Practise gravity with a falling ball. Grade 1.',
            'image_upload_ids':[upload['upload_id']],'materials':['Ball'],'instructions':'Observe the ball falling. Compare its direction.','supervision':'Parent supervision required.',
            'availability':'Available','paths':[{'topic_id':topic}]}).json()
        r=client.post('/api/v1/admin/activity-kits/'+kit['id']+'/publish',json={'expected_version':kit['version']});assert r.status_code==200,r.text;kit=r.json()
        admin=client.app.dependency_overrides[require_admin]()['id']
        with client.app.state.database.session() as db,db.begin():
            conversation=ConversationSession(student_id=UUID(admin),mode='study',curriculum_id=UUID(cid),revision=revision,
                context_snapshot={'curriculum_id':cid,'level_id':level,'subject_id':subject,'domain_id':domain,'category_id':None,'topic_id':topic,'subtopic_id':leaf})
            db.add(conversation);db.flush();sid=str(conversation.id)
        n=0
        def turn(question,answer):
            nonlocal n
            from sqlalchemy import select, func
            with client.app.state.database.session() as db,db.begin():
                n=(db.scalar(select(func.max(Message.turn_number)).where(Message.session_id==UUID(sid))) or 0)+1
                db.add(Message(session_id=UUID(sid),role='user',turn_number=n,blocks=[{'kind':'text','text':question}]))
                row=Message(session_id=UUID(sid),role='assistant',turn_number=n,blocks=[{'kind':'text','text':answer}],resolved_curriculum_id=UUID(cid),resolved_subject_id=UUID(subject),resolved_topic_id=UUID(topic),resolved_revision=revision)
                db.add(row);db.flush();mid=str(row.id)
            r=client.get('/api/v1/sessions/'+sid+'/recommendations',params={'message_id':mid});assert r.status_code==200,r.text
            return mid,r.json()
        def choice(result):return result['recommendation_decision']['primary']
        def card_seen(mid,c):
            r=client.post('/api/v1/sessions/'+sid+'/recommendations/displayed',json={'message_id':mid,'candidate_id':c['candidate_id'],'version':c['version']});assert r.status_code==200,r.text
        first,r=turn('Explain force','Force is a push or pull.');assert choice(r)['candidate_id']==force['id'] and choice(r)['display_mode']=='inline';assert r['teachers']==[]
        assert client.post('/api/v1/sessions/'+sid+'/images/displayed',json={'message_id':first,'resource_id':force['id'],'resource_version':force['version']}).status_code==200
        _,r=turn('Another example','Force pushes a door.');assert choice(r)['display_mode']=='reference earlier'
        mid,r=turn('Explain gravity','Gravity pulls a falling ball down.');assert choice(r)['candidate_id']==gravity['id'];assert len(r['resources'])==1
        mid,r=turn('Show how it works','Gravity pulls a ball down.');c=choice(r);assert c['candidate_id']==video['id'] and c['display_mode']=='optional card';card_seen(mid,c)
        _,r=turn('Show how it works','Gravity pulls a falling ball down.');assert choice(r)['display_mode']=='reference earlier'
        _,r=turn('Show the gravity video again','Gravity makes a ball fall.');assert choice(r)['candidate_id']==video['id'] and choice(r)['display_mode']=='optional card'
        kmid,r=turn('Test my understanding','Practise gravity using a falling ball.');assert choice(r)['candidate_id']==kit['id'] and r['kits'][0]['materials']==['Ball'];card_seen(kmid,choice(r))
        opened=client.get('/api/v1/sessions/'+sid+'/recommendations/'+kit['id'],params={'message_id':kmid});assert opened.status_code==200 and opened.json()['item']['instructions']==kit['instructions']
        tmid,r=turn('I need a tutor','A tutor can help explain gravity.');assert choice(r)['candidate_id']==teacher['id'];assert choice(r)['availability_state']=='unknown';assert len(r['teachers'])==1
        _,r=turn('Explain evaporation','Water changes to gas.');assert r['recommendation_decision']['display_mode']=='none' and not r['resources'] and not r['kits']
        reopened=client.get('/api/v1/sessions/'+sid+'/recommendations',params={'message_id':first}).json();assert reopened['image_decision']['displayed'] is True
        # Recheck publication on open; earlier selection is not rewritten with another kit.
        assert client.post('/api/v1/admin/activity-kits/'+kit['id']+'/unpublish',json={'expected_version':kit['version']}).status_code==200
        assert client.get('/api/v1/sessions/'+sid+'/recommendations/'+kit['id'],params={'message_id':kmid}).status_code==404
        assert client.post('/api/v1/admin/teachers/'+teacher['id']+'/unpublish',json={'expected_version':teacher['version']}).status_code==200
        assert client.get('/api/v1/sessions/'+sid+'/recommendations/'+teacher['id'],params={'message_id':tmid}).status_code==404
        class IntentGateway:
            available=True
            calls=0
            broken=False
            def generate(self,messages):
                self.calls+=1
                assert any('<flame-intent>' in m['content'] for m in messages)
                metadata='broken' if self.broken else '{"intent":"demonstrate","concept":"gravity","language":"en"}'
                return Generated('Gravity pulls objects down. <flame-intent>'+metadata+'</flame-intent>','fixture',20,10)
        gateway=IntentGateway();client.app.state.gateway=gateway
        body={'mode':'study','question':'Show how gravity works','context':conversation.context_snapshot}
        key=uuid4().hex;route='/api/v1/sessions/'+sid+'/ask'
        r=client.post(route,json=body,headers={'Idempotency-Key':key});assert r.status_code==200,r.text
        assert r.json()['blocks'][0]['text']=='Gravity pulls objects down.' and r.json()['learning_need']['intent']=='demonstrate'
        assert r.json()['learning_response']['answer']['blocks']==r.json()['blocks']
        assert r.json()['learning_response']['recommendations']['status']=='pending'
        assert client.post(route,json=body,headers={'Idempotency-Key':key}).json()==r.json() and gateway.calls==1
        selected=client.get('/api/v1/sessions/'+sid+'/recommendations',params={'message_id':r.json()['message_id']}).json()
        assert selected['recommendation_decision']['intent_source']=='llm'
        gateway.broken=True
        r=client.post(route,json=body,headers={'Idempotency-Key':uuid4().hex});assert r.status_code==200,r.text
        assert r.json()['blocks'][0]['text']=='Gravity pulls objects down.' and 'learning_need' not in r.json()
        selected=client.get('/api/v1/sessions/'+sid+'/recommendations',params={'message_id':r.json()['message_id']}).json()
        assert selected['recommendation_decision']['intent_source']=='fallback'
        # Legacy image JSON is decoded without replacing or rewriting its saved choice.
        from copy import deepcopy
        from app.modules.functional.recommendation_history.models import RecommendationSet
        from sqlalchemy import select
        legacy_id,_=turn('Explain force','Force is a push or pull.')
        legacy={'schema_version':1,'resource_id':force['id'],'resource_version':force['version'],'display_mode':'inline',
            'reason':'Saved legacy image choice','displayed':True,'reference_message_id':None}
        with client.app.state.database.session() as db,db.begin():
            saved=db.scalar(select(RecommendationSet).where(RecommendationSet.message_id==UUID(legacy_id)))
            saved.image_decision=deepcopy(legacy);saved.resource_ids=[];saved.teacher_ids=[]
        reopened=client.get('/api/v1/sessions/'+sid+'/recommendations',params={'message_id':legacy_id}).json()
        assert reopened['image_decision']==legacy and 'recommendation_decision' not in reopened
        with client.app.state.database.session() as db:
            assert db.scalar(select(RecommendationSet).where(RecommendationSet.message_id==UUID(legacy_id))).image_decision==legacy
        # Composer failure does not rewrite completed answers or emit a fake none decision.
        from app.modules.application.recommendations import router as recommendation_router
        with monkeypatch.context() as patch:
            def fail_selection(*args,**kwargs):raise TimeoutError('private diagnostic')
            patch.setattr(recommendation_router.service,'recommend',fail_selection)
            unavailable=client.get('/api/v1/sessions/'+sid+'/recommendations',params={'message_id':first})
            assert unavailable.status_code==200 and unavailable.json()['learning_response']['recommendations']['status']=='unavailable'
            assert 'private diagnostic' not in unavailable.text
        assert client.post(route,json=body,headers={'Idempotency-Key':key}).status_code==200
        # Owning recommendation cleanup runs before message/session FK deletion.
        deletion=client.request('DELETE','/api/v1/sessions/'+sid,json={'confirm':True})
        assert deletion.status_code==200,deletion.text
        with client.app.state.database.session() as db:
            assert not db.scalars(select(RecommendationSet).where(RecommendationSet.session_id==UUID(sid))).all()
            assert db.get(ConversationSession,UUID(sid)) is None
        client.app.dependency_overrides[require_member]=lambda:{'id':str(uuid4()),'role':'member'}
        assert client.get('/api/v1/sessions/'+sid+'/recommendations',params={'message_id':first}).status_code==404
