from django.shortcuts import render,redirect,get_object_or_404
from django.views.generic import (TemplateView,CreateView,FormView,View)
from django.contrib.auth import authenticate,login,logout
from .forms import UserForm,RegistForm,UserLoginForm,CustomUserCreationForm,UserEditForm,forms
from django.urls import reverse_lazy
from .models import (Anime,Genres,Seasons,Studios,Tags,User_anime_relations,VoiceActor,Song,Character,Artist)
from django.db.models import F,Q
import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import requests
from django.contrib.auth.views import PasswordResetDoneView

class PasswordResetDone(PasswordResetDoneView):
    """パスワード変更用URLを送りましたページ"""
    template_name = 'registration/password_reset_done.html'

def kata2hira(text):
    """
    カタカナをひらがなに変換する関数
    """
    result = []
    for char in text:
        if isinstance(char, str) and len(char) == 1:  # 1文字かを確認
            # カタカナの範囲（「ァ」～「ン」）をひらがなに変換
            if 'ァ' <= char <= 'ン':
                result.append(chr(ord(char) - 0x60))  # カタカナからひらがなに変換
            else:
                result.append(char)  # カタカナでない場合はそのまま追加
        else:
            result.append(char)  # 文字列全体が長すぎる場合、そのまま追加
    return ''.join(result)


class UserLoginView(FormView):
    template_name = 'html/user_login.html'
    form_class = UserLoginForm
    success_url = reverse_lazy('anime_tracker:home')
    
    def form_valid(self, form):
        email = form.cleaned_data['email']
        password = form.cleaned_data['password']
        remember = form.cleaned_data['remember']
        user = authenticate(email=email,password=password)
        if user:
            login(self.request,user)
            if remember:
                self.request.session.set_expiry(120000)  # 秒間保持
            else:
                self.request.session.set_expiry(0)  # ブラウザが閉じられると終了
            return super().form_valid(form)
        # 認証に失敗した場合、フォームを無効にしてエラーメッセージを表示
        form.add_error('password', 'メールアドレスまたはパスワードが間違っています。')
        return self.form_invalid(form)
    
    def form_invalid(self, form):
        # フォームが無効な場合、フォームを再度表示（エラーメッセージを含む）
        return render(self.request, self.template_name, {'form': form})

class UserLogoutView(View):
    def get(self,request,*args, **kwargs):
        return render(request,'user_logout.html')
    
    def post(self,request,*args, **kwargs):
        logout(request)
        return redirect('anime_tracker:home')

class RegistUseView(CreateView):
    template_name = 'html/regist.html'
    form_class = RegistForm
    success_url = reverse_lazy('anime:home')

# アニメのリストを取得し、フィルタリング、並び替えを行う共通メソッド
def get_animes(request, status, sort_option,search_conditions):
    user_anime_ids = User_anime_relations.objects.filter(user_id=request.user.id).values_list('anime_id', flat=True)
    
    
    # ステータスごとのフィルタリング
    if status == 'watched':  # 視聴済
        animes = Anime.objects.filter(user_anime_relations__status=2, user_anime_relations__user_id=request.user.id)
        print('視聴済')
    elif status == 'favorite':  # お気に入り
        animes = Anime.objects.filter(user_anime_relations__is_favorite=True, user_anime_relations__user_id=request.user.id)
        print('お気に入り')
    elif status == 'plan_to_watch':  # 視聴予定
        animes = Anime.objects.filter(user_anime_relations__status=1, user_anime_relations__user_id=request.user.id)
        print('視聴予定')
    elif status == 'not_in_list':  # リスト外
        animes = Anime.objects.all()
        print('リスト外')
    else:  # 無効なステータスの場合、全て非表示
        animes = Anime.objects.all()
        print('全て非表示')

    


    # 検索条件の追加
    # AND検索のために条件をまとめる
    filter_conditions = Q()
    
    # 検索キーワードに対してAND検索を行う
    if search_conditions.get('search'):
        search_keywords = search_conditions['search']
        for keyword in search_keywords:
            # タイトル検索（タイトルにキーワードが含まれている場合）
            filter_conditions &= Q(title__icontains=keyword)

            # 他のテーブル（ジャンル、タグ、キャラクター、ソング、声優、アーティストなど）にも適用
            genres = Genres.objects.filter(name__icontains=keyword)
            tags = Tags.objects.filter(name__icontains=keyword)
            characters = Character.objects.filter(name__icontains=keyword)
            voice_actors = VoiceActor.objects.filter(name__icontains=keyword)
            songs = Song.objects.filter(title__icontains=keyword)
            artists = Artist.objects.filter(name__icontains=keyword)



    # フィルタリングを適用
    animes = animes.filter(filter_conditions)
                                
    
    

    # ジャンル検索
    if search_conditions.get('genre'):
        filter_conditions &= Q(genres__id__in=search_conditions['genre'])
        print(f"ジャンルフィルタ: {filter_conditions}")
    
    # タグ検索
    if search_conditions.get('tag'):
        filter_conditions &= Q(tags__id__in=search_conditions['tag'])
        print(f"タグフィルタ: {filter_conditions}")
    
    # シーズン検索
    if search_conditions.get('season'):
        filter_conditions &= Q(seasons__id__in=search_conditions['season'])
        print(f"シーズンフィルタ: {filter_conditions}")
    
    # スタジオ検索
    if search_conditions.get('studio'):
        filter_conditions &= Q(studios__id__in=search_conditions['studio'])
        print(f"スタジオフィルタ: {filter_conditions}")

    # デバッグ: filter_conditionsが正しく設定されているか確認
    print(f"filter_conditions: {filter_conditions}")
    
    # フィルタリングを適用
    animes = animes.filter(filter_conditions)

        
    print("sort_option:" + sort_option)
    
    # 並び順の適用
    if sort_option == 'average_rating':
        animes = animes.order_by('-average_rating')
        print('平均評価が高い')
    elif sort_option == 'season-asc':
        animes = animes.order_by('start_date')  # 古い順
        print('古い順')
    elif sort_option == 'season-desc':
        animes = animes.order_by('-start_date')  # 新しい順
        print('新しい順')
    elif sort_option == 'watched_count-desc':
        animes = animes.order_by('-watched_count')
        print('登録数')
    else:
        animes = animes.order_by('-start_date')  # デフォルトでは新しい順
        print('外：新しい順')


    # 重複を排除
    animes = animes.distinct()

    # 重複を手動で排除（Python側で重複を取り除く）
    unique_animes = {}
    for anime in animes:
        unique_animes[anime.id] = anime

    # 重複を排除したアニメリストを返す
    return list(unique_animes.values())


def index(request):
    return render(request, 'html/index.html')


# homeビュー
def home(request):
    # URLパラメータから条件を取得
    sort_option = request.GET.get('sort', 'start-date-desc')  # デフォルトは新しい順
    status = request.GET.get('status', 'not_in_list')  # デフォルトはリスト外
    
    # URLのクエリパラメータから検索条件を取得
    genre_search = request.GET.getlist('genre')
    print(" genre_search ")
    print( genre_search )
    tag_search = request.GET.getlist('tag')
    print("tag_search")
    print(tag_search)
    season_search = request.GET.getlist('season')
    print("season_search")
    print(season_search)
    studio_search = request.GET.getlist('studio')
    print("studio_search")
    print(studio_search)
    search_query = request.GET.getlist('search')   # 検索バーのキーワードを取得
    print("studio_search")
    print(studio_search)
    
    # ユーザーの入力をひらがなに変換
    # ユーザーの入力をカタカナ→ひらがなに変換
    search_query_hiragana = kata2hira(search_query)  # カタカナをひらがなに変換
    
    # スペースで区切ってキーワードリストを作成
    search_keywords = search_query_hiragana.split() if search_query_hiragana else []
    
    # 出力確認用
    print("search_query_hiragana:", search_query_hiragana)  # 変換後のひらがな
    print("search_keywords:", search_keywords)  # スペースで区切ったキーワードリスト
    
    # 検索条件をまとめてディクショナリに格納
    search_conditions = {
        'genre': genre_search,
        'tag': tag_search,
        'season': season_search,
        'studio': studio_search,
        'search': search_query,
    }
    
    # データを取得
    genres = Genres.objects.all()
    tags = Tags.objects.all()
    studios = Studios.objects.all()
    seasons = Seasons.objects.all()
    
    
    # 未ログインの場合、ステータスを「リスト外」に強制
    if not request.user.is_authenticated:
        status = 'not_in_list'
    

    # アニメのリストを取得
    animes = get_animes(request, status, sort_option, search_conditions)
    
    

    return render(request, 'html/home.html', {
        'animes': animes,
        'genres': genres,
        'tags': tags,
        'studios': studios,
        'seasons': seasons,
        'status': status , # 現在のステータスをテンプレートに渡す
        'search_conditions': search_conditions,#検索条件
    })


def regist_view(request):
    user_form = CustomUserCreationForm(request.POST or None)  
    
    # フォームの状態をコンソールに表示
    print("フォームのデータ:", user_form.data)  # POSTデータが渡されているか確認
    print("フォームのバリデーション:", user_form.is_valid())  # True or False
    print("フォームのエラー:", user_form.errors)  # バリデーションエラーの詳細
    
    
    
    if user_form.is_valid():
        user_form.save()
        return redirect('anime_tracker:user_login')  # 登録成功後にログイン画面へリダイレクト
    else:
        # フォームのエラーをコンソールに出力
        print("Form errors:", user_form.errors)

    return render(request, 'html/regist.html', context={
        'user_form': user_form,
    })

@login_required
def user_edit(request):
    if request.method == 'POST':
        form = UserEditForm(request.POST, user=request.user, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'プロフィールが更新されました。')
            return render(request, 'html/user_edit.html', {'form': form})  # アカウント設定画面のまま
    else:
        form = UserEditForm(user=request.user, instance=request.user)

    return render(request, 'html/user_edit.html', {'form': form})







#アニメ詳細画面で追加
@login_required
def update_status(request):
    print('update_statusが呼び出された')
    if request.method == "POST":
        # 生のリクエストボディを出力
        print("リクエストボディ:", request.body)
        try:
            # JSONデータを読み取る
            data = json.loads(request.body)  # リクエストボディをJSONとして解析
            anime_id = data.get('anime_id')  # JSONからアニメIDを取得
            status = data.get('status')      # JSONからステータスを取得

            print(f"アニメID: {anime_id}")
            print(f"ステータス: {status}")
            
            anime = get_object_or_404(Anime, id=anime_id)
            user = request.user
            print(f"リクエストユーザー: {user.nickname}")
            # デバッグ用の出力

            # ユーザーとアニメの関係を更新
            relation, created = User_anime_relations.objects.get_or_create(user_id=user, anime_id=anime)

            # ステータス更新処理
            if status == "watched":
                relation.status = 2  # 視聴済みに変更
            elif status == "favorite":
                if relation.status == 2:  # 視聴済みのみお気に入りに設定可能
                    relation.is_favorite = True
            elif status == "plan_to_watch":
                relation.status = 1  # 視聴予定に変更
                relation.is_favorite = False  # 視聴予定の場合はお気に入りを解除

            relation.save()

            # JSONレスポンスの内容
            return JsonResponse({
                "status": relation.status,  # 1: 視聴予定, 2: 視聴済み
                "is_favorite": relation.is_favorite,  # お気に入りの状態
            })

        except Exception as e:
            print(f"Anime の取得でエラー: {e}")
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request method."}, status=400)


#アニメ視聴管理更新
def animeDetailView(request, pk):
    anime = get_object_or_404(Anime, pk=pk)
    user_relation = None
    if request.user.is_authenticated:
        user_relation = User_anime_relations.objects.filter(user_id=request.user, anime_id=anime).first()
    related_animes = Anime.objects.filter(series_id=anime.series_id).exclude(id=anime.id)
    print(related_animes.count())
    return render(request, 'html/anime_detail.html', {'anime': anime, 'user_relation': user_relation,'related_animes': related_animes})

#ユーザー評価入力
def update_rating(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            anime_id = data.get('anime_id')
            rating = data.get('rating')

            if not 0.0 <= rating <= 5.0:
                return JsonResponse({"error": "Invalid rating value."}, status=400)

            anime = get_object_or_404(Anime, id=anime_id)
            user = request.user
            relation, created = User_anime_relations.objects.get_or_create(user_id=user, anime_id=anime)
            relation.rating = rating
            relation.save()
            
            print("relation更新"+ str(relation.rating))
            # アニメの平均評価を更新


            return JsonResponse({"message": "Rating updated successfully.", "average_rating": anime.average_rating})
            # return JsonResponse({"message": "Rating updated successfully."})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Invalid request method."}, status=400)

def search_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)  # リクエストボディをJSONで読み込み
        
        animes = Anime.objects.all()

        if 'genre' in data:
            animes = animes.filter(genres__id__in=data['genre'])  # ジャンルに基づく検索
        if 'tag' in data:
            animes = animes.filter(tags__id__in=data['tag'])      # タグに基づく検索
        if 'season' in data:
            animes = animes.filter(seasons__id__in=data['season']) # シーズンに基づく検索
        if 'studio' in data:
            animes = animes.filter(studios__id__in=data['studio']) # 制作スタジオに基づく検索

        # 重複を排除
        animes = animes.distinct()
        
        print("search_view実行") 
        print(animes.query) 

        # JSON形式で結果を返す
        results = [
            {
                'id': anime.id,
                'title': anime.title,
                'thumbnail': anime.thumbnail.url if anime.thumbnail else '',
            } for anime in animes
        ]
        # JSON形式で結果を返す
        results = [
            {
                'id': anime.id,
                'title': anime.title,
                'thumbnail': anime.thumbnail.url if anime.thumbnail else '',
            } for anime in animes
        ]
        return JsonResponse({'results': results})

    return JsonResponse({'error': 'Invalid request method'}, status=400)



