"""Module boundary, compatibility and nonblocking composition regression gates."""
import ast
from pathlib import Path
from uuid import uuid4
import pytest
from fastapi import HTTPException
from app.core.database import Base
from app.modules.recommendations.models import RecommendationSet
from app.modules.resources.models import RecommendationSet as LegacyRecommendationSet
from app.modules.learning_response import composer, service
from app.modules.recommendations import service as recommendation_service
from app.modules.recommendations.router import router
from app.modules.resources.recommendations_router import router as legacy_router
from app.modules.resources.image_selection import decide_image as legacy_image
from app.modules.recommendations.image_selection import decide_image


def test_table_and_router_aliases_have_one_owner_and_no_schema_change():
    assert LegacyRecommendationSet is RecommendationSet
    assert Base.metadata.tables['flame.recommendation_sets'] is RecommendationSet.__table__
    assert legacy_router is router
    assert legacy_image is decide_image
    assert RecommendationSet.__module__ == 'app.modules.recommendations.models'
    assert {route.path for route in router.routes} == {
        '/api/v1/sessions/{session_id}/recommendations', '/api/v1/sessions/{session_id}/images/displayed',
        '/api/v1/sessions/{session_id}/recommendations/displayed', '/api/v1/sessions/{session_id}/recommendations/{candidate_id}'}


def test_coordinator_consumes_interfaces_without_foreign_models_or_admin_routers():
    source=Path(recommendation_service.__file__).read_text()
    imports=[node.module for node in ast.walk(ast.parse(source)) if isinstance(node,ast.ImportFrom)]
    assert not any(name and (name.endswith('.models') or name.endswith('.router')) for name in imports)
    assert 'app.modules.resources.candidates' in imports
    assert 'app.modules.teachers.candidates' in imports
    assert 'app.modules.activity_kits.candidates' in imports
    assert 'app.modules.conversations.recommendation_context' in imports


def test_composer_returns_answer_without_ever_loading_recommendations(monkeypatch):
    from types import SimpleNamespace
    mid,rid=str(uuid4()),str(uuid4())
    answer={'status':'ok','message_id':mid,'request_id':rid,'blocks':[{'kind':'text','text':'Explanation'}]}
    calls=[]
    monkeypatch.setattr(service,'teaching_ask',lambda *a,**kw:(calls.append(kw) or answer))
    result=service.ask(None,None,uuid4(),uuid4(),'same-key',SimpleNamespace(mode='study'),daily_limit=17)
    assert result['blocks'] is answer['blocks'] and result['message_id']==mid
    assert result['learning_response']['recommendations']['status']=='pending'
    assert calls==[{'daily_limit':17}] and 'learning_response' not in answer
    assert service.ask(None,None,uuid4(),uuid4(),'same-key',SimpleNamespace(mode='study'),daily_limit=17)==result
    assert composer.compose_answer(answer,mode='curiosity')['learning_response']['recommendations']['status']=='none'


@pytest.mark.parametrize('error,code',[(TimeoutError(),'recommendation_timeout'),(RuntimeError('private diagnostic'),'recommendation_unavailable')])
def test_recommendation_failures_are_isolated_and_sanitized(error,code):
    def failed():raise error
    result=composer.compose_recommendations(uuid4(),failed)
    assert result['status']=='unavailable' and result['resources']==[]
    assert result['learning_response']['recommendations']=={'status':'unavailable','data':None,'code':code}
    assert 'private diagnostic' not in str(result)


def test_composer_keeps_authorization_failures_and_none_distinct():
    def denied():raise HTTPException(404,'session_not_found')
    with pytest.raises(HTTPException) as failure:composer.compose_recommendations(uuid4(),denied)
    assert failure.value.status_code==404
    mid=uuid4();empty={'status':'no_results','resources':[],'teachers':[]}
    assert composer.compose_recommendations(mid,lambda:empty)['learning_response']['recommendations']['status']=='none'
    data={'status':'ok','resources':[{'id':str(uuid4())}],'teachers':[]}
    result=composer.compose_recommendations(mid,lambda:data)
    assert result['learning_response']['recommendations']['data']==data and 'learning_response' not in data
