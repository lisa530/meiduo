let vm = new Vue({
    el: "#app", // 通过id选择器 找到绑定的html
    //修改vue读取变量的语法
     delimiters: ['[[', ']]'],
    // 数据对象
    data:{
        //v-model
        username: '',
        password: '',
        password2: '',
        mobile: '',
        allow:'',
        image_code_url: '',
        uuid: '',
        image_code: '',
        sms_code: '',
        sms_code_tip: '获取短信验证码',
        send_flag: false, //发送短信标记

        //v-show,控制是否展示错误信息，默认为flase不展示
        error_name: false,
        error_password: false,
        error_password2: false,
        error_mobile: false,
        error_allow: false,
        error_image_code: false, // 图形验证码
         error_sms_code: false, // 短信验证码


        //错误提示信息error_message
        error_name_message: '', // 用户名错误提示信息
        error_mobile_message: '',   // 手机号错误提示信息
        error_image_code_message: '', // 图形验证码错误提示信息
        error_sms_code_message: '',

    },

     mounted() { // 页面加载完会被调用的
        // 生成图形验证码
        this.generate_image_code();
    },
    //绑定事件
    methods:{
        // 发送短信验证码
        send_sms_code(){
            // 避免用户恶意频繁点击发送短信验证码标签
            if (this.send_flag == true) { // 表示已经发送短信
                return; // 返回
            }
            this.send_flag = true; // 将发送短信标记设置为true
            // 校验数据：mobile，image_code
            this.check_mobile();
            this.check_image_code();
			// 只要其中有一个数据校验失败，将发送短信标记设置为false,并返回
            if (this.error_mobile == true || this.error_image_code == true) {
                this.send_flag = false;
                return;
            }

            this.send_flag = true; // 将发送短信标记设置为true
            let url = '/sms_codes/' + this.mobile + '/?image_code=' + this.image_code + '&uuid=' + this.uuid;
            axios.get(url,{
                responseType: 'json' // 返回数据类型
            })
                .then(response =>{ // 请求成功
                    if (response.data.code == 0){
                        // 展示发送短信倒计时60秒效果
                        let num = 60;
                        let t = setInterval(()=>{
                            if (num == 1){ // 倒计时结束
                                // 停止回调函数的执行
                                clearInterval(t)
                                // 还原sms_code_tip的提示信息
                                this.sms_code_tip = '获取短信验证码';
                                this.generate_image_code(); // 生成新生成图形验证码
                                this.send_flag = false; // 将发送短信标记设置为false
                            }else{ // 正在倒计时
                                num -= 1;
                                this.sms_code_tip = num + '秒';

                            }
                        },1000)
                    }else {
                        if (response.data.code == '4001') { // 状态码4001，图形验证码错误
                            this.error_image_code_message = response.data.errmsg;
                            this.error_image_code = true;

                        }
                        this.send_flag = false;
                    }
                })
                .catch(error =>{
                    console.log(error)
                    this.send_flag = false;
                })
        },

        // 生成图形验证码的方法：封装的思想，代码复用
        generate_image_code() {
            this.uuid = generateUUID();
            this.image_code_url = '/image_codes/' + this.uuid + '/';
        },

        // 校验用户名
        check_username() {
            // 用户名是5-20个字符，[a-zA-Z0-9_-]
            // 定义正则
            let re = /^[a-zA-Z0-9_-]{5,20}$/;
            // 使用正则匹配用户名数据
            if (re.test(this.username)) {
                // 匹配成功，不展示错误提示信息
                this.error_name = false;
            } else {
                // 匹配失败，展示错误提示信息
                this.error_name_message = '请输入5-20个字符的用户名';
                this.error_name = true;
            }

            // 判断用户名是否重复注册
            if (this.error_name == false){ //只有当用户输入的用户名满足条件时才会去判断
                let url = '/usernames/' + this.username +'/count/';
                axios.get(url,{
                    responseType: 'json' // 后端返回的数据类型
                })
                    // 请求成功，从响应体中中取出count的值
                    .then(response =>{
                        if (response.data.count == 1 ){
                           this.error_name_message = '用户名已存在';
                           // 将error_name 的值改为true（展示错误信息)
                           this.error_name = true;
                        }else{
                            this.error_name = false;
                        }

                    })
                    //请示失败 控制台输出错误信息
                    .catch(error =>{
                        console.log(error.response);
                    })

            }
        },
        // 校验密码
        check_password(){
            let re = /^[0-9A-Za-z]{8,20}$/;
            if (re.test(this.password)){
                // 密码验证通过 error_password = flase 不展示错误信息
                this.error_password = false;
            }else{
                this.error_password = true;
            }
        },
        // 校验确认密码
        check_password2() {
            if (this.password != this.password2) {
                this.error_password2 = true;
            } else {
                this.error_password2 = false;
            }
        },
         // 校验手机号
        check_mobile(){
        let re = /^1[3-9]\d{9}$/;
        if(re.test(this.mobile)) {
            this.error_mobile = false;
        } else {
            this.error_mobile_message = '您输入的手机号格式不正确';
            this.error_mobile = true;
            }

        // 判断手机号是否重复注册
        if (this.error_mobile == false){
            let url = '/mobiles/' + this.mobile + '/count/';
            axios.get(url,{
                responseType: 'json'
            })
                .then(response =>{
                // 手机号存在 将error_mobile的值改为 true
                if (response.data.count == 1){
                    this.error_mobile_message = '手机号已存在';
                    this.error_mobile = true;
                }else{
                    this.error_mobile = false;
                }

             })
                .catch(error =>{
                    console.log(error.response)
            })
        }
        },
        // 校验图形验证码
        check_image_code(){
            if (this.image_code.length != 4){
                this.error_image_code_message = '请输入图形验证码';
                this.error_image_code = true;

            }else {
                this.error_image_code = false;
            }
        },
        // 校验短信验证码
        check_sms_code(){
            if(this.sms_code.length != 6){
                this.error_sms_code_message = '请填写短信验证码';
                this.error_sms_code = true;
            } else {
                this.error_sms_code = false;
            }
    },

        // 校验是否勾选协议
        check_allow(){
            if(!this.allow) {
            this.error_allow = true;
        } else {
            this.error_allow = false;
        }

        },
        // 监听表单提交事件
        on_submit(){
            this.check_username();
            this.check_password();
            this.check_password2();
            this.check_mobile();
            this.check_sms_code();
            this.check_allow();

            if (this.error_name == true || this.error_password == true || this.error_password2 == true|| this.error_mobile == true ||this.error_sms_code == true || this.error_allow == true) {
                // 禁用掉表单的提交事件
                window.event.returnValue = false;
            }
        },
    }
});